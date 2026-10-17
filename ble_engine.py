#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BLE 引擎(与界面框架无关, 可被 Qt/Tk 等复用)
========================================================================
通过电脑蓝牙(BLE)连接低功耗蓝牙透传模块(如 HC-04 / HM-10 / AT-09 / CC2541 / JDY-23 等),
实现 电脑 <-> 模块 <-> MCU 的无线串口通信。

引擎在独立线程中运行 asyncio 事件循环(bleak), 通过线程安全的事件队列与界面通信:
    {"type": "device_found" / "services" / "uart_ready" / "rx" / "tx" /
             "log" / "error" / "conn_state" / "scan_state" /
             "periodic_started" / "periodic_stopped"}
"""

import asyncio
import threading
import time

from i18n import tr

try:
    from bleak import BleakScanner, BleakClient
except ImportError:
    raise SystemExit("缺少依赖库 bleak, 请先执行: pip install -r requirements.txt")

# ---------------------------------------------------------------------------
# 常见 BLE 透传服务 UUID
# ---------------------------------------------------------------------------
# Nordic UART Service (nRF 系透传, 如 JDY-23 / 部分固件)
NUS_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
NUS_WRITE_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"   # 写入: 电脑 -> 模块 -> MCU
NUS_NOTIFY_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # 通知: MCU -> 模块 -> 电脑

# HC-04 / HM-10 / AT-09 等: 服务 0xFFE0 + 透传特征 0xFFE1, 写入与通知共用同一特征
# (HC-04 手册 V2.6: AT+SUUID 默认 FFE0, AT+TUUID 默认 FFE1, 均可通过 AT 指令修改)
HC_SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
HC_TRANSPARENT_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

# ISSC/Microchip 透传服务 (HC 官方上位机 HC-PC 的备选固件)
ISSC_SERVICE_UUID = "49535343-fe7d-4ae5-8fa9-9fafd205e455"
ISSC_WRITE_UUID = "49535343-8841-43f4-a8d4-ecbe34729bb3"
ISSC_NOTIFY_UUID = "49535343-1e4d-4bd9-ba61-23c647249616"

# 自动回退挑选特征时跳过的系统服务(不会是串口透传数据通道)
SKIP_SERVICE_UUIDS = {
    "00001800-0000-1000-8000-00805f9b34fb",  # Generic Access
    "00001801-0000-1000-8000-00805f9b34fb",  # Generic Attribute
    "0000180a-0000-1000-8000-00805f9b34fb",  # Device Information
    "0000180f-0000-1000-8000-00805f9b34fb",  # Battery Service
    "00001812-0000-1000-8000-00805f9b34fb",  # HID
    "00001813-0000-1000-8000-00805f9b34fb",  # Scan Parameters
}

KNOWN_UUIDS = {
    NUS_SERVICE_UUID: "Nordic UART 服务",
    NUS_WRITE_UUID: "RX 写入特征",
    NUS_NOTIFY_UUID: "TX 通知特征",
    HC_SERVICE_UUID: "HC-04/HM-10 透传服务",
    HC_TRANSPARENT_UUID: "透传特征(写入/通知)",
    ISSC_SERVICE_UUID: "ISSC 透传服务",
    ISSC_WRITE_UUID: "ISSC 写入特征",
    ISSC_NOTIFY_UUID: "ISSC 通知特征",
    "0000fff0-0000-1000-8000-00805f9b34fb": "HC-04 搜索过滤服务(LUUID)",
    "00001800-0000-1000-8000-00805f9b34fb": "Generic Access 服务",
    "00001801-0000-1000-8000-00805f9b34fb": "Generic Attribute 服务",
    "0000180a-0000-1000-8000-00805f9b34fb": "Device Information 服务",
    "00002a00-0000-1000-8000-00805f9b34fb": "设备名称特征",
    "00002a01-0000-1000-8000-00805f9b34fb": "外观特征",
}


# ---------------------------------------------------------------------------
# 发送/显示工具
# ---------------------------------------------------------------------------
def build_data(cfg):
    """根据配置把发送内容转成字节流。cfg: dict(cmd, fmt, encoding, line)"""
    fmt = (cfg.get("fmt") or "ascii").lower()
    if fmt == "hex":
        s = "".join((cfg.get("cmd") or "").split())
        if not s:
            return b""
        if len(s) % 2 != 0 or any(ch not in "0123456789abcdefABCDEF" for ch in s):
            raise ValueError(tr("HEX 格式不正确: 需要偶数个十六进制字符, 例如: AA 55 01 0D 0A"))
        return bytes.fromhex(s)
    text = cfg.get("cmd") or ""
    line = cfg.get("line") or ""
    enc = (cfg.get("encoding") or "utf-8").lower()
    if enc == "gbk":
        return (text + line).encode("gbk", errors="replace")
    return (text + line).encode("utf-8", errors="replace")


def format_bytes(data, mode):
    """把收到的字节流按显示模式转成文本"""
    mode = (mode or "ascii").lower()
    if mode == "hex":
        return " ".join("%02X" % b for b in data)
    if mode == "mixed":
        hex_part = " ".join("%02X" % b for b in data)
        ascii_part = data.decode("utf-8", errors="replace")
        ascii_part = ascii_part.replace("\r", "\\r").replace("\n", "\\n")
        return "%s  |  %s" % (hex_part, ascii_part)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# BLE 引擎: 独立线程中运行 asyncio 事件循环, 通过事件回调与 UI 通信
# ---------------------------------------------------------------------------
class BleEngine:
    def __init__(self, sink):
        self.sink = sink              # 事件回调 (线程安全)
        self.loop = None
        self._thread = None

        self.client = None
        self.write_char = None        # 写入特征
        self.notify_char = None       # 通知特征

        self.scanner = None
        self._scan_stop = None
        self._scan_active = False

        self._periodic_stop = None
        # 连接看门狗: 远端断电/走远时主动发现掉线(Windows 链路超时往往很慢)
        self._watchdog_task = None
        self._intentional_disconnect = False
        # 定时发送使用的配置快照(线程间只传字符串, 由 UI 侧定时刷新)
        self.periodic_cfg = {"cmd": "", "fmt": "ascii", "encoding": "utf-8", "line": ""}

    # ---------------- 事件循环 ----------------
    def start(self):
        self._thread = threading.Thread(target=self._run_loop, name="ble-loop", daemon=True)
        self._thread.start()
        while self.loop is None:
            time.sleep(0.005)

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def post(self, event):
        try:
            self.sink(event)
        except Exception:
            pass

    def submit(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    # ---------------- 扫描 ----------------
    async def _scan_loop(self, seconds=30):
        self._scan_stop = asyncio.Event()
        self.scanner = BleakScanner(detection_callback=self._on_device)
        self.post({"type": "scan_state", "state": "scanning"})
        try:
            await self.scanner.start()
            try:
                if seconds is None:
                    await self._scan_stop.wait()   # 持续扫描, 直到主动停止
                else:
                    await asyncio.wait_for(self._scan_stop.wait(), timeout=seconds)
            except asyncio.TimeoutError:
                pass
        except Exception as e:
            self.post({"type": "error", "text": tr("扫描出错: %s") % e})
        finally:
            try:
                await self.scanner.stop()
            except Exception:
                pass
            self.scanner = None
            self._scan_active = False
            self.post({"type": "scan_state", "state": "stopped"})

    def start_scan(self, seconds=None):
        if self._scan_active:
            return
        self._scan_active = True
        self.submit(self._scan_loop(seconds))

    def stop_scan(self):
        if self._scan_stop is not None:
            self.submit(self._scan_stop.set())

    def _on_device(self, device, adv):
        self.post({
            "type": "device_found",
            "name": device.name or tr("(未命名)"),
            "address": device.address,
            "rssi": getattr(adv, "rssi", None) if adv is not None else None,
        })

    # ---------------- 连接 ----------------
    async def _connect(self, address):
        self.post({"type": "conn_state", "state": "connecting"})
        try:
            self.client = BleakClient(address, timeout=15,
                                      disconnected_callback=self._on_ble_disconnected)
            await self.client.connect()
            await self._setup_uart()
            self.post({"type": "conn_state", "state": "connected"})
            self._start_watchdog()
        except Exception as e:
            if self.client is not None:
                try:
                    await self.client.disconnect()
                except Exception:
                    pass
            self.client = None
            self.write_char = None
            self.notify_char = None
            self.post({"type": "error", "text": tr("连接失败: %s") % e})
            self.post({"type": "conn_state", "state": "idle"})

    def _on_ble_disconnected(self, client):
        """Windows 报告链路断开(远端断电/走远)时由 bleak 回调; 在引擎线程执行。"""
        if self._intentional_disconnect or self.client is not client:
            return
        self.client = None
        self.write_char = None
        self.notify_char = None
        self._cancel_watchdog()
        if self._periodic_stop is not None:
            self._periodic_stop.set()
            self._periodic_stop = None
        self.post({"type": "log", "tag": "warn",
                   "text": tr("[断开] 远端设备已断开(断电或超出范围)")})
        self.post({"type": "conn_state", "state": "idle"})

    # ---------------- 连接看门狗 ----------------
    def _pick_probe_char(self):
        """挑一个只读特征做心跳探测: 优先透传特征本身, 否则任意可读特征。"""
        for c in (self.notify_char, self.write_char):
            if c is not None and "read" in getattr(c, "properties", []):
                return c
        try:
            for svc in self.client.services:
                for c in svc.characteristics:
                    if "read" in c.properties:
                        return c
        except Exception:
            pass
        return None

    def _start_watchdog(self):
        self._cancel_watchdog()
        self._watchdog_task = self.submit(self._watchdog())

    def _cancel_watchdog(self):
        t = self._watchdog_task
        self._watchdog_task = None
        if t is not None:
            try:
                t.cancel()
            except Exception:
                pass

    async def _watchdog(self):
        """每 2s 轻量读一次特征; 连续 2 次失败/超时即判定远端掉线并断开。
        无只读特征的设备退化为只依赖 disconnected_callback。"""
        client = self.client
        probe = self._pick_probe_char()
        fails = 0
        try:
            while self.client is client:
                await asyncio.sleep(2.0)
                if self.client is not client:
                    return
                if probe is None:
                    continue
                try:
                    await asyncio.wait_for(client.read_gatt_char(probe), timeout=3.0)
                    fails = 0
                except Exception:
                    fails += 1
                    if fails >= 2:
                        self.post({"type": "log", "tag": "warn",
                                   "text": tr("[断开] 远端无响应(断电或超出范围), 已断开")})
                        self._watchdog_task = None
                        await self._disconnect()
                        return
        except asyncio.CancelledError:
            pass

    def connect(self, address):
        self.submit(self._connect(address))

    async def _setup_uart(self):
        # bleak 3.x: connect 后自动完成服务发现
        services_info = []
        svc_list = list(self.client.services)
        for svc in svc_list:
            chars = [{"uuid": str(c.uuid), "props": sorted(c.properties)}
                     for c in svc.characteristics]
            services_info.append({"uuid": str(svc.uuid), "characteristics": chars})
        if not services_info:
            raise RuntimeError(tr("设备未暴露任何 GATT 服务"))
        self.post({"type": "services", "services": services_info})

        # ---- 自动识别常见透传服务(按可靠程度依次尝试) ----
        self.write_char = None
        self.notify_char = None
        recognized = None

        def find_char(uuid):
            for svc in svc_list:
                for c in svc.characteristics:
                    if str(c.uuid).lower() == uuid:
                        return c
            return None

        # 1) Nordic UART (NUS): 写入/通知为分离特征
        w, n = find_char(NUS_WRITE_UUID), find_char(NUS_NOTIFY_UUID)
        if w is not None and n is not None:
            self.write_char, self.notify_char = w, n
            recognized = "Nordic UART 标准服务(NUS)"

        # 2) HC-04 / HM-10 / AT-09: 透传特征 0xFFE1, 写入与通知共用同一特征
        if recognized is None:
            c = find_char(HC_TRANSPARENT_UUID)
            if c is not None:
                props = c.properties
                if (("write" in props or "write-without-response" in props)
                        and "notify" in props):
                    self.write_char = self.notify_char = c
                    recognized = "HC-04/HM-10 透传服务(FFE0/FFE1)"

        # 3) ISSC/Microchip 透传 (HC 官方上位机的备选固件)
        if recognized is None:
            w, n = find_char(ISSC_WRITE_UUID), find_char(ISSC_NOTIFY_UUID)
            if w is not None and n is not None:
                self.write_char, self.notify_char = w, n
                recognized = "ISSC 透传服务(49535343)"

        if recognized is None:
            # 回退1: 同一服务内"可写特征 + 通知特征"成对出现(典型写/读分离模块);
            #        通知端优先挑"纯通知"特征(只 notify 不可写), 避免误选双向特征
            for svc in svc_list:
                if str(svc.uuid).lower() in SKIP_SERVICE_UUIDS:
                    continue
                writable = [c for c in svc.characteristics
                            if "write" in c.properties or "write-without-response" in c.properties]
                notifiable = [c for c in svc.characteristics if "notify" in c.properties]
                if writable and notifiable:
                    pure_notify = [c for c in notifiable
                                   if "write" not in c.properties
                                   and "write-without-response" not in c.properties]
                    self.write_char = writable[0]
                    self.notify_char = (pure_notify or notifiable)[0]
                    break
            # 回退2: 同一特征同时可写+可通知 (单特征双向透传, 自定义 UUID 模块常见形态)
            if self.write_char is None or self.notify_char is None:
                for svc in svc_list:
                    if str(svc.uuid).lower() in SKIP_SERVICE_UUIDS:
                        continue
                    for c in svc.characteristics:
                        props = c.properties
                        if (("write" in props or "write-without-response" in props)
                                and "notify" in props):
                            self.write_char = self.notify_char = c
                            break
                    if self.write_char is not None:
                        break
            # 回退3: 任意可写特征 + 任意可通知特征
            if self.write_char is None or self.notify_char is None:
                for svc in svc_list:
                    if str(svc.uuid).lower() in SKIP_SERVICE_UUIDS:
                        continue
                    for c in svc.characteristics:
                        props = c.properties
                        if self.write_char is None and ("write" in props or "write-without-response" in props):
                            self.write_char = c
                        if self.notify_char is None and "notify" in props:
                            self.notify_char = c
            if self.write_char is None or self.notify_char is None:
                raise RuntimeError(tr("未找到可用的写入/通知特征, 请在左侧手动指定"))
            if self.write_char is self.notify_char:
                self.post({"type": "log", "tag": "info",
                           "text": tr("[提示] 识别到自定义透传特征 %s (写入/通知共用同一特征, 已自动选择)")
                                   % self.write_char.uuid})
            else:
                self.post({"type": "log", "tag": "warn",
                           "text": tr("[提示] 未识别到已知透传服务, 已自动选择: 写入=%s 通知=%s (可在左侧手动修改)")
                                   % (self.write_char.uuid, self.notify_char.uuid)})
        else:
            self.post({"type": "log", "tag": "info",
                       "text": tr("[提示] 已识别到 %s, 读写特征已自动配置") % tr(recognized)})

        # 通知订阅失败不中断连接: 收发仍可先用, 可手动"应用特征设置"重试订阅
        if self.notify_char is not None:
            try:
                await self.client.start_notify(self.notify_char, self._on_notify)
            except Exception as e:
                self.post({"type": "log", "tag": "warn",
                           "text": tr("[警告] 通知订阅失败: %s (可点[应用特征设置]重试)") % e})
        self.post({"type": "uart_ready",
                   "write": str(self.write_char.uuid),
                   "notify": str(self.notify_char.uuid),
                   "mtu": getattr(self.client, "mtu_size", 23)})
        self.post({"type": "log", "tag": "info",
                   "text": tr("[连接] 已连接 %s, MTU=%s")
                           % (self.client.address, getattr(self.client, "mtu_size", 23))})

    def _on_notify(self, sender, data):
        # 通知真正到达的瞬间打时间戳, 避免 UI 批量处理事件时偏差
        self.post({"type": "rx", "data": bytes(data), "ts": time.time()})

    # ---------------- 发送 ----------------
    async def _write(self, data):
        if self.client is None or self.write_char is None:
            raise RuntimeError(tr("未连接或未设置写入特征"))
        props = self.write_char.properties
        # 优先无应答写(write command), 与手机端 BLE 工具一致; 部分模块只处理无应答写
        if "write-without-response" in props:
            response = False
        elif "write" in props:
            response = True
        else:
            raise RuntimeError(tr("写入特征缺少可写属性"))
        t_send = time.time()
        self.post({"type": "tx", "data": data, "ts": t_send})
        await self.client.write_gatt_char(self.write_char, data, response=response)

    def send(self, data):
        if not data:
            return
        fut = self.submit(self._write(data))
        fut.add_done_callback(self._send_done)

    def _send_done(self, fut):
        try:
            fut.result()
        except Exception as e:
            self.post({"type": "error", "text": tr("发送失败: %s") % e})

    # ---------------- 定时发送 ----------------
    async def _periodic_loop(self, interval):
        self._periodic_stop = asyncio.Event()
        self.post({"type": "periodic_started"})
        try:
            while not self._periodic_stop.is_set():
                await asyncio.sleep(interval)
                if self.client is None or self.write_char is None:
                    break
                data = build_data(self.periodic_cfg)
                if data:
                    await self._write(data)
        except Exception as e:
            self.post({"type": "error", "text": tr("定时发送已停止: %s") % e})
        finally:
            self._periodic_stop = None
            self.post({"type": "periodic_stopped"})

    def start_periodic(self, interval):
        if self._periodic_stop is None:
            self.submit(self._periodic_loop(interval))

    def stop_periodic(self):
        if self._periodic_stop is not None:
            self.submit(self._periodic_stop.set())

    # ---------------- 手动指定特征(已连接时) ----------------
    def apply_chars(self, write_uuid, notify_uuid):
        async def _apply():
            if self.client is None:
                return
            try:
                if self.notify_char is not None:
                    try:
                        await self.client.stop_notify(self.notify_char)
                    except Exception:
                        pass   # 未订阅过时不至于中断手动指定
                self.write_char = None
                self.notify_char = None
                for svc in list(self.client.services):
                    for c in svc.characteristics:
                        u = str(c.uuid).lower()
                        if u == write_uuid.lower():
                            self.write_char = c
                        if u == notify_uuid.lower():
                            self.notify_char = c
                if self.notify_char is not None and "notify" in self.notify_char.properties:
                    await self.client.start_notify(self.notify_char, self._on_notify)
                if self.write_char is None or self.notify_char is None:
                    self.post({"type": "error", "text": tr("指定的特征无效")})
                    return
                self.post({"type": "log", "tag": "info",
                           "text": tr("[特征] 已手动应用 写入=%s 通知=%s") % (write_uuid, notify_uuid)})
            except Exception as e:
                self.post({"type": "error", "text": tr("应用特征失败: %s") % e})
        self.submit(_apply())

    # ---------------- 断开 ----------------
    async def _disconnect(self):
        self._intentional_disconnect = True
        try:
            self._cancel_watchdog()
            if self._periodic_stop is not None:
                self._periodic_stop.set()
                self._periodic_stop = None
            if self.client is not None:
                try:
                    if self.notify_char is not None:
                        await self.client.stop_notify(self.notify_char)
                    await self.client.disconnect()
                except Exception as e:
                    self.post({"type": "log", "tag": "warn", "text": tr("[断开] %s") % e})
            self.client = None
            self.write_char = None
            self.notify_char = None
            self.post({"type": "log", "tag": "info", "text": tr("[断开] 已断开连接")})
            self.post({"type": "conn_state", "state": "idle"})
        finally:
            self._intentional_disconnect = False

    def disconnect(self):
        self.submit(self._disconnect())

    def shutdown(self):
        self._cancel_watchdog()
        if self._periodic_stop is not None:
            try:
                asyncio.run_coroutine_threadsafe(self._periodic_stop.set(), self.loop)
            except Exception:
                pass
        if self.client is not None:
            try:
                asyncio.run_coroutine_threadsafe(self._disconnect(), self.loop)
            except Exception:
                pass
        if self._scan_active and self._scan_stop is not None:
            try:
                asyncio.run_coroutine_threadsafe(self._scan_stop.set(), self.loop)
            except Exception:
                pass
