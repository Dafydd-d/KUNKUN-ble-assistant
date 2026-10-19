# -*- coding: utf-8 -*-
"""特征应用结果回显: 成功跟随、失败回退到应用前组合(下拉=引擎真实生效状态)。"""
import os
import sys

proj = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, proj)
os.chdir(proj)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets, QtTest

import ble_serial_assistant as appmod

appmod.MainWindow._start_scan = lambda self: None
appmod.MainWindow._save_config = lambda self: None

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
    ]},
]

applied = []
w.engine.apply_chars = lambda a, b: applied.append((a, b))

w.conn_state = "connected"
w._conn_addr = "FF:26:06:16:06:CD"
w._on_services(services)
w._on_uart_ready({"write": FFF7, "notify": FFF7, "mtu": 516})
assert w.cb_write.currentData() == FFF7

# ---- 用户改下拉 -> 应用失败 -> 引擎回退, 下拉跟着回到应用前组合 ----
w.cb_write.setCurrentIndex(w.cb_write.findData(FFB1))
w.cb_notify.setCurrentIndex(w.cb_notify.findData(FFB2))
QtTest.QTest.qWait(500)
assert applied == [(FFB1, FFB2)], applied
w._on_event({"type": "chars_applied", "ok": False, "write": FFF7, "notify": FFF7})
assert w.cb_write.currentData() == FFF7, w.cb_write.currentData()
assert w.cb_notify.currentData() == FFF7, w.cb_notify.currentData()

# ---- 回退不得触发再次应用(信号已屏蔽) ----
QtTest.QTest.qWait(500)
assert applied == [(FFB1, FFB2)], applied

# ---- 再改一次 -> 成功 -> 下拉显示引擎生效组合 ----
w.cb_write.setCurrentIndex(w.cb_write.findData(FFB1))
w.cb_notify.setCurrentIndex(w.cb_notify.findData(FFB2))
QtTest.QTest.qWait(500)
w._on_event({"type": "chars_applied", "ok": True, "write": FFB1, "notify": FFB2})
assert w.cb_write.currentData() == FFB1 and w.cb_notify.currentData() == FFB2

# ---- 引擎已无可用特征(空)时保留界面选择, 不清空 ----
w._on_event({"type": "chars_applied", "ok": False, "write": "", "notify": ""})
assert w.cb_write.currentData() == FFB1 and w.cb_notify.currentData() == FFB2

print("CHARS SYNC PASS")
