# -*- coding: utf-8 -*-
"""下拉锚定回归: 打开弹层时当前项是首行, 选项不出现在当前选择上方。"""
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

# ---- 选中第2项后打开弹层: 当前项转到首行, 其余按原序循环跟随 ----
w.cb_line.setCurrentIndex(1)
assert w.cb_line.currentData() == "\r"
w.cb_line.showPopup()
qapp.processEvents()
items = [(w.cb_line.itemText(i), w.cb_line.itemData(i)) for i in range(w.cb_line.count())]
assert items[0][1] == "\r", items
assert [d for _, d in items] == ["\r", "\n", "\r\n", ""], items
assert w.cb_line.currentIndex() == 0 and w.cb_line.currentData() == "\r"
w.cb_line.hidePopup()

# ---- 弹层左上角对齐框的左上角(图10形式) ----
cont = w.cb_line.view().parentWidget()
g = w.cb_line.mapToGlobal(QtCore.QPoint(0, 0))
assert abs(cont.x() - g.x()) <= 2 and abs(cont.y() - g.y()) <= 2, (cont.x(), cont.y(), g.x(), g.y())

# ---- 旋转不丢条目, 查找按值依旧可用 ----
assert sorted(w.cb_line.findData(d) for d in ("", "\r", "\n", "\r\n")) == [0, 1, 2, 3]
assert w.cb_line.findData("\r\n") >= 0

# ---- 首项选中时列表保持原序(与图10一致) ----
w.cb_encoding.setCurrentIndex(0)
w.cb_encoding.showPopup()
qapp.processEvents()
assert [w.cb_encoding.itemText(i) for i in range(2)] == ["utf-8", "gbk"]
w.cb_encoding.hidePopup()

# ---- 换选后再次打开, 新的当前项到首行 ----
w.cb_encoding.setCurrentIndex(1)   # gbk
w.cb_encoding.showPopup()
qapp.processEvents()
assert w.cb_encoding.itemText(0) == "gbk" and w.cb_encoding.currentText() == "gbk"
w.cb_encoding.hidePopup()

print("COMBO PASS")
