# -*- coding: utf-8 -*-
"""下拉弹层视觉回归: 选中行左缘点亮指示胶囊+圆角槽底, ASCII 机器词条等宽字。"""
import os
import sys

proj = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, proj)
os.chdir(proj)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets

import ble_serial_assistant as appmod

appmod.MainWindow._start_scan = lambda self: None
appmod.MainWindow._save_config = lambda self: None

qapp = QtWidgets.QApplication(sys.argv[:1])
qapp.setStyle("Fusion")
w = appmod.MainWindow()
w.show()
qapp.processEvents()


def grab_popup(cb):
    cb.showPopup()
    qapp.processEvents()
    img = cb.view().parentWidget().grab().toImage()
    cb.hidePopup()
    qapp.processEvents()
    return img


def rgb(img, x, y):
    c = QtGui.QColor(img.pixel(x, y))
    return (c.red(), c.green(), c.blue())


def hx(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def near(c1, c2, tol=20):
    return all(abs(a - b) <= tol for a, b in zip(c1, c2))


ROW = appmod.PopupItemDelegate.ROW_H

# ---- 浅色主题: 行尾下拉, 选中项 \r 停在原位(第2行)高亮 ----
w.cb_line.setCurrentIndex(1)   # \r
assert w.cb_line.currentData() == "\r"
img = grab_popup(w.cb_line)
assert img.width() > 40 and img.height() >= 4 * ROW, (img.width(), img.height())
img.save(os.path.join(os.environ.get("TEMP", "."), "ble_popup_light.png"))

tok = appmod.THEMES["light"]
y_free = ROW // 2                  # 首行(无, 未选中)中心
y_sel = ROW + ROW // 2             # 第二行(\r, 选中)中心, 顺序固定停在原位
# 选中行: 左缘指示胶囊点亮为 ACCENT, 行底是浅色高亮槽
assert near(rgb(img, 7, y_sel), hx(tok["ACCENT"])), rgb(img, 7, y_sel)
assert near(rgb(img, img.width() - 8, y_sel), hx(tok["POPUP_SEL_BG"])), rgb(img, img.width() - 8, y_sel)
# 未选中行: 胶囊槽位是面板底色, 无高亮
assert near(rgb(img, 7, y_free), hx(tok["PANEL"])), rgb(img, 7, y_free)
assert near(rgb(img, img.width() - 8, y_free), hx(tok["PANEL"])), rgb(img, img.width() - 8, y_free)

# ---- 双字体: ASCII 机器词条等宽, 自然语词界面字 ----
model = w.cb_line.model()
delg = w.cb_line.view().itemDelegate()
opt = QtWidgets.QStyleOptionViewItem()
delg.initStyleOption(opt, model.index(1, 0))          # \r
assert "Consolas" in opt.font.families(), opt.font.families()
delg.initStyleOption(opt, model.index(0, 0))          # 无
assert opt.font.families()[0] == "Microsoft YaHei UI", opt.font.families()

# ---- 门脸字随词条走(与弹层同一条规则) ----
assert "Consolas" in w.cb_line.font().families(), w.cb_line.font().families()
w.cb_line.setCurrentIndex(0)                          # 无
assert w.cb_line.font().families()[0] == "Microsoft YaHei UI", w.cb_line.font().families()
w.cb_line.setCurrentIndex(1)                          # 回到 \r
assert "Consolas" in w.cb_line.font().families(), w.cb_line.font().families()

# ---- 深色主题热切换后弹层换色(电台面板琥珀系) ----
w._set_theme("dark")
qapp.processEvents()
img = grab_popup(w.cb_line)
img.save(os.path.join(os.environ.get("TEMP", "."), "ble_popup_dark.png"))
tok = appmod.THEMES["dark"]
assert near(rgb(img, 7, y_sel), hx(tok["ACCENT"])), rgb(img, 7, y_sel)
assert near(rgb(img, img.width() - 8, y_sel), hx(tok["POPUP_SEL_BG"])), rgb(img, img.width() - 8, y_sel)

print("COMBO STYLE PASS")
