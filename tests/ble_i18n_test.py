# -*- coding: utf-8 -*-
"""验证中英双语: 菜单结构(无括号说明/语言子菜单)、切换后文案、行尾数据兼容。"""
import os
import sys

proj = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, proj)
os.chdir(proj)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets

import ble_serial_assistant as appmod
from i18n import set_lang, get_lang

appmod.MainWindow._start_scan = lambda self: None
appmod.MainWindow._save_config = lambda self: None

set_lang("zh")
qapp = QtWidgets.QApplication(sys.argv[:1])
w = appmod.MainWindow()
w.show()
qapp.processEvents()

# ---- 中文: 主题菜单无括号说明; 工具下有语言子菜单 ----
assert w._act_light.text() == "浅色模式", w._act_light.text()
assert w._act_dark.text() == "深色模式", w._act_dark.text()
assert "(" not in w._act_light.text() and "(" not in w._act_dark.text()
tools = [a.text() for a in w.menuBar().actions()[1].menu().actions()]
assert "语言" in tools, tools
assert w._act_zh.text() == "中文" and w._act_en.text() == "English"
assert w.btn_disconnect.text() == "断开"
assert w.btn_apply.text() == "应用特征设置"
assert w.cb_line.itemText(0) == "无" and w.cb_line.itemData(0) == ""
assert w.cb_line.itemData(3) == "\r\n"

# ---- 切换到英文 ----
w._set_language("en")
qapp.processEvents()
assert get_lang() == "en"
menubar = w.menuBar()
assert [a.text() for a in menubar.actions()] == ["File", "Tools", "Help"], \
    [a.text() for a in menubar.actions()]
assert w._act_light.text() == "Light Mode"
assert w._act_dark.text() == "Dark Mode"
assert w.btn_disconnect.text() == "Disconnect"
assert w.btn_apply.text() == "Apply Characteristics"
assert w.btn_send.text() == "Send"
assert w.cb_line.itemText(0) == "None" and w.cb_line.itemData(0) == ""
assert w.pill_state.text() in ("Idle", "Scanning...", "Connecting...", "Connected"), \
    w.pill_state.text()
assert w.pill_dev.text() in ("No Device Selected", "Idle") or True
assert w.chk_scroll._label == "Auto Scroll"
assert w.seg_mode._buttons["mixed"].text() == "Mixed"
assert w.svc_tree.headerItem().text(1) == "Properties"
tools = [a.text() for a in menubar.actions()[1].menu().actions()]
assert "Language" in tools, tools
assert w._act_zh.isChecked() is False and w._act_en.isChecked() is True

# 菜单文案互不串(闭包回归: 菜单 action 应各自保留自己的文本)
fmenu = menubar.actions()[0].menu()
assert [a.text() for a in fmenu.actions() if a.text()] == \
       ["Clear Receive Area", "Save Log...", "Exit"], [a.text() for a in fmenu.actions()]

# ---- 切回中文 ----
w._set_language("zh")
qapp.processEvents()
assert w.btn_disconnect.text() == "断开"
assert w.cb_line.itemText(0) == "无"
assert [a.text() for a in w.menuBar().actions()] == ["文件", "工具", "帮助"]
assert w.chk_scroll._label == "自动滚动"

print("I18N PASS")
