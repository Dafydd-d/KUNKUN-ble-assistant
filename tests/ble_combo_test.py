# -*- coding: utf-8 -*-
"""下拉锚定回归: 列表顺序固定, 不随选择/开关弹层变化; 弹层贴框向下展开。"""
import os
import sys

proj = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, proj)
os.chdir(proj)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

import ble_serial_assistant as appmod

appmod.MainWindow._start_scan = lambda self: None
appmod.MainWindow._save_config = lambda self: None

qapp = QtWidgets.QApplication(sys.argv[:1])
qapp.setStyle("Fusion")
w = appmod.MainWindow()
w.show()
qapp.processEvents()


def snapshot(cb):
    return [(cb.itemText(i), cb.itemData(i)) for i in range(cb.count())]


# ---- 原始顺序固定: 无, \r, \n, \r\n ----
origin = snapshot(w.cb_line)
assert [d for _, d in origin] == ["", "\r", "\n", "\r\n"], origin

# ---- 选中第2项后打开弹层: 顺序不变, 选中项停在原位 ----
w.cb_line.setCurrentIndex(1)
assert w.cb_line.currentData() == "\r"
w.cb_line.showPopup()
qapp.processEvents()
assert snapshot(w.cb_line) == origin, snapshot(w.cb_line)
assert w.cb_line.currentIndex() == 1 and w.cb_line.currentData() == "\r"
w.cb_line.hidePopup()

# ---- 弹层贴框下沿向下展开, 不遮挡门脸(框内当前值) ----
cont = w.cb_line.view().parentWidget()
g = w.cb_line.mapToGlobal(QtCore.QPoint(0, w.cb_line.height()))
assert abs(cont.x() - g.x()) <= 2 and abs(cont.y() - g.y()) <= 2, (cont.x(), cont.y(), g.x(), g.y())
assert cont.y() >= w.cb_line.mapToGlobal(QtCore.QPoint(0, 0)).y(), "弹层不得盖住门脸"

# ---- 反复换选+开关弹层, 列表结构始终不变(波特率下拉式固定顺序) ----
for idx in (3, 0, 2, 1):
    w.cb_line.setCurrentIndex(idx)
    w.cb_line.showPopup()
    qapp.processEvents()
    assert snapshot(w.cb_line) == origin, (idx, snapshot(w.cb_line))
    assert w.cb_line.currentIndex() == idx and w.cb_line.currentData() == origin[idx][1]
    w.cb_line.hidePopup()
qapp.processEvents()

# ---- 查找按值依旧可用 ----
assert sorted(w.cb_line.findData(d) for d in ("", "\r", "\n", "\r\n")) == [0, 1, 2, 3]
assert w.cb_line.findData("\r\n") == 3

# ---- 编码下拉同样固定顺序(utf-8 在前, gbk 在后) ----
w.cb_encoding.setCurrentIndex(1)   # gbk
w.cb_encoding.showPopup()
qapp.processEvents()
assert [w.cb_encoding.itemText(i) for i in range(2)] == ["utf-8", "gbk"]
assert w.cb_encoding.currentIndex() == 1 and w.cb_encoding.currentText() == "gbk"
w.cb_encoding.hidePopup()

print("COMBO PASS")
