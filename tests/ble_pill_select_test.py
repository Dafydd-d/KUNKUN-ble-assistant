# -*- coding: utf-8 -*-
"""验证 pill_dev 标签: 拖选可用、Ctrl+C/双击/右键可复制、同文本刷新不清选区、高亮可见。"""
import os
import sys

proj = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, proj)
os.chdir(proj)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets, QtTest

import ble_serial_assistant as appmod

# 不真扫蓝牙
appmod.MainWindow._start_scan = lambda self: None

qapp = QtWidgets.QApplication(sys.argv[:1])
w = appmod.MainWindow()
w.show()
qapp.processEvents()

lbl = w.pill_dev
assert isinstance(lbl, appmod.CopyableLabel), "pill_dev 不是 CopyableLabel: %r" % type(lbl)
assert lbl.textInteractionFlags() & QtCore.Qt.TextSelectableByMouse, "未开启鼠标拖选"

# 模拟已连接状态与设备文本
addr = "C4:26:04:03:0E:2B"
w.conn_state = "connected"
w._conn_addr = addr
w.devices[addr] = {"name": "HC-04BLE", "rssi": -50}
w._update_status()
assert lbl.text() == "HC-04BLE (C4:26:04:03:0E:2B)", "标签文本: %r" % lbl.text()

# ---- 1. 鼠标拖选 ----
lbl.adjustSize()
qapp.processEvents()
size = lbl.size()
y = size.height() // 2
QtTest.QTest.mousePress(lbl, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, QtCore.QPoint(2, y))
QtTest.QTest.mouseMove(lbl, QtCore.QPoint(size.width() - 2, y), delay=30)
QtTest.QTest.mouseRelease(lbl, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier,
                          QtCore.QPoint(size.width() - 2, y))
sel = lbl.selectedText()
print("拖选结果 selectedText =", repr(sel))
assert sel, "拖选没有产生选区"

# ---- 2. Ctrl+C 复制选中 ----
qapp.clipboard().setText("")
QtTest.QTest.keyClick(lbl, QtCore.Qt.Key_C, QtCore.Qt.ControlModifier)
copied = qapp.clipboard().text()
print("Ctrl+C 剪贴板 =", repr(copied))
assert copied == sel, "Ctrl+C 未复制选中内容"

# ---- 3. 同文本状态刷新后选区保留 ----
w._status_dirty = True
w._flush_lines()
print("刷新后 selectedText =", repr(lbl.selectedText()))
assert lbl.selectedText() == sel, "同文本刷新清掉了选区"

# ---- 4. 选中高亮可见(像素里应出现 ACCENT 色) ----
img = lbl.grab().toImage()
acc = QtGui.QColor(w.tok["ACCENT"])
hits = 0
for xx in range(img.width()):
    for yy in range(img.height()):
        c = QtGui.QColor(img.pixel(xx, yy))
        if (abs(c.red() - acc.red()) < 30 and abs(c.green() - acc.green()) < 30
                and abs(c.blue() - acc.blue()) < 30):
            hits += 1
print("高亮像素命中 =", hits)
assert hits > 0, "选中高亮不可见"

# ---- 5. 双击整段复制 ----
qapp.clipboard().setText("")
QtTest.QTest.mouseDClick(lbl, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, QtCore.QPoint(size.width() // 2, y))
copied_all = qapp.clipboard().text()
print("双击剪贴板 =", repr(copied_all))
assert copied_all == "HC-04BLE (C4:26:04:03:0E:2B)", "双击未复制整段文本"

print("ALL PASS")
