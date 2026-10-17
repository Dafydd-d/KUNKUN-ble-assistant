# -*- coding: utf-8 -*-
"""验证特征选择链路: 手动指定被记住、重连自动套用、下拉变更自动应用。"""
import os
import sys

proj = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, proj)
os.chdir(proj)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets, QtTest

import ble_serial_assistant as appmod

appmod.MainWindow._start_scan = lambda self: None
saved = []
appmod.MainWindow._save_config = lambda self: saved.append(dict(self._char_prefs))

qapp = QtWidgets.QApplication(sys.argv[:1])
w = appmod.MainWindow()
w._char_prefs.clear()   # 不受真实配置文件里的记忆影响
w.show()
qapp.processEvents()

FFB1 = "0000ffb1-0000-1000-8000-00805f9b34fb"
FFB2 = "0000ffb2-0000-1000-8000-00805f9b34fb"
FFF7 = "0000fff7-0000-1000-8000-00805f9b34fb"

services = [
    {"uuid": "0000ffb0-0000-1000-8000-00805f9b34fb", "characteristics": [
        {"uuid": FFB1, "props": ["read", "write", "write-without-response"]},
        {"uuid": FFB2, "props": ["notify", "read"]},
    ]},
    {"uuid": "0000fff6-0000-1000-8000-00805f9b34fb", "characteristics": [
        {"uuid": FFF7, "props": ["notify", "write", "write-without-response"]},
        {"uuid": "0000fff8-0000-1000-8000-00805f9b34fb", "props": ["write", "write-without-response"]},
    ]},
]

applied = []
w.engine.apply_chars = lambda a, b: applied.append((a, b))

# ---- 第一次连接: 自动识别选了 fff7(模拟旧固件误选), 无记忆 ----
w.conn_state = "connected"
w._conn_addr = "FF:26:06:16:06:CD"
w._on_services(services)
w._on_uart_ready({"write": FFF7, "notify": FFF7, "mtu": 516})
assert w.cb_write.currentData() == FFF7, w.cb_write.currentData()

# ---- 用户手动改下拉 -> 防抖后自动应用一次并记住 ----
w.cb_write.setCurrentIndex(w.cb_write.findData(FFB1))
w.cb_notify.setCurrentIndex(w.cb_notify.findData(FFB2))
QtTest.QTest.qWait(500)
assert applied == [(FFB1, FFB2)], applied
assert w._char_prefs["FF:26:06:16:06:CD"] == {"write": FFB1, "notify": FFB2}, w._char_prefs
assert saved and saved[-1]["FF:26:06:16:06:CD"]["write"] == FFB1

# ---- 重连: 自动识别仍是 fff7, 记忆应自动切回 ffb1/ffb2 并重订通知 ----
applied.clear()
w._on_services(services)
w._on_uart_ready({"write": FFF7, "notify": FFF7, "mtu": 516})
assert w.cb_write.currentData() == FFB1, w.cb_write.currentData()
assert w.cb_notify.currentData() == FFB2, w.cb_notify.currentData()
assert (FFB1, FFB2) in applied, applied

# ---- 无记忆时保持自动识别的选择 ----
w._char_prefs.clear()
applied.clear()
w._on_services(services)
w._on_uart_ready({"write": FFB1, "notify": FFB2, "mtu": 516})
assert w.cb_write.currentData() == FFB1 and w.cb_notify.currentData() == FFB2
assert applied == [], applied   # 引擎已订阅, 不必重复应用

print("CHARS PASS")
