# -*- coding: utf-8 -*-
"""验证设备列表过期清理: 停播设备移除, 连接中设备保留。"""
import os
import sys
import time

proj = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, proj)
os.chdir(proj)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets

import ble_serial_assistant as appmod

appmod.MainWindow._start_scan = lambda self: None
appmod.MainWindow._save_config = lambda self: None

qapp = QtWidgets.QApplication(sys.argv[:1])
w = appmod.MainWindow()
w.show()
qapp.processEvents()

A = "FF:26:06:16:06:CD"   # 将保持连接的设备
B = "FF:26:06:16:06:D7"   # 将断电消失的设备

for addr, name in ((A, "DevA"), (B, "DevB")):
    w._on_event({"type": "device_found", "address": addr, "name": name, "rssi": -40})
w._flush_devices()
assert set(w.cards) == {A, B}, set(w.cards)

# 选中 DevB, 然后连接 DevA; DevB 停播超过阈值
w._select_device(B)
w.conn_state = "connecting"
w._conn_addr = A
w.devices[B]["seen"] = time.time() - appmod.DEV_STALE_SEC - 5
w.devices[A]["seen"] = time.time() - appmod.DEV_STALE_SEC - 5
w._flush_devices()

assert set(w.cards) == {A}, set(w.cards)          # DevB 消失, 连接中的 DevA 保留
assert B not in w.devices
assert w.selected_addr is None                    # 选中的设备消失后取消选中

# 断开后 DevA 若继续停播也会消失; 恢复广播则保留
w.conn_state = "idle"
w._conn_addr = None
w._flush_devices()
assert A not in w.cards

w._on_event({"type": "device_found", "address": A, "name": "DevA", "rssi": -40})
w._flush_devices()
assert A in w.cards

print("EXPIRE PASS")
