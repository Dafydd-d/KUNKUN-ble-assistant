# 坤坤蓝牙助手

Windows BLE 无线串口调试助手 —— 电脑 ↔ BLE 透传模块（HC-04 / HM-10 / NUS / ISSC 等）↔ MCU。

A Windows BLE serial debug tool for transparent UART modules between PC and MCU.

## 功能

- **自动扫描**：启动即持续扫描附近 BLE 设备，双击卡片一键连接；断电消失的设备自动从列表清理
- **自动识别特征**：支持 HC-04/HM-10（FFE0/FFE1）、Nordic UART（NUS）、ISSC 及自定义透传特征，也可手动指定（按设备记忆，重连自动套用）
- **收发显示**：ASCII / HEX / 混合模式，毫秒时间戳，收发统计
- **发送**：ASCII/HEX、utf-8/gbk 编码、行尾可选、定时发送（轮询）、8 个预设命令
- **日志**：自动记录 / 手动保存
- **界面**：浅色 / 深色主题，中文 / English 双语，设备名与 MAC 可拖选复制

## 快速开始

**方式一：直接运行**

在 GitHub [Releases](../../releases) 页面下载最新的 `坤坤蓝牙助手.exe`，双击运行（Windows 10 及以上，需有蓝牙适配器）。

**方式二：源码运行**

需要 Python 3.10 以上（开发环境为 3.12）：

```bash
pip install -r requirements.txt
python ble_serial_assistant.py
```

或双击 `启动.bat`。

## 使用

1. 给蓝牙模块上电，打开程序（自动持续扫描）
2. 在左侧列表选中你的模块（可按名称过滤），双击卡片连接
3. 连接后自动识别读写特征；识别不准时在「写入 / 通知」下拉中手动指定并点击「应用特征设置」
4. 选择格式（ASCII/HEX）和行尾，输入命令后点【发送】
5. MCU 的回复实时显示在监视屏

详细说明见 [使用说明.md](使用说明.md)。

## 常见问题

| 现象 | 原因与处理 |
| --- | --- |
| 连接超时 / 设备未找到 | 多半被手机 APP 等其他设备占用（多数模块只允许一个连接），断开手机并给模块重新上电 |
| 发送后没有回复 | 检查「写入 / 通知」特征是否选对；选错通道数据会被模块忽略。特征选择会按设备记忆 |
| 信号显示 -127 或不变化 | -127 是「无测量值」占位符；设备连接后不再广播，显示的是最后一次广播时的信号 |
| 单次能发多少字节 | 受 MTU 限制：单包净荷 = MTU − 3 字节（如 MTU=516 时为 513 字节），超过需自行拆包 |

## 项目结构

```
ble_serial_assistant.py   界面 (PySide6)
ble_engine.py             BLE 引擎 (bleak, asyncio 独立线程)
i18n.py                   中英双语词条
tests/                    界面回归测试(无头运行, 无需蓝牙)
启动.bat                   源码启动脚本
BLE串口助手.spec            PyInstaller 打包配置
使用说明.md                 详细使用说明
```

## 测试

回归测试无头运行、不依赖蓝牙硬件，改动代码后跑一遍即可：

```bash
python tests/ble_chars_test.py
```

## 打包

```bash
pyinstaller BLE串口助手.spec
```

产物在 `dist/坤坤蓝牙助手.exe`。

## 依赖

- [PySide6](https://doc.qt.io/qtforpython/) — 界面
- [bleak](https://github.com/hbldh/bleak) — 跨平台 BLE 通信
