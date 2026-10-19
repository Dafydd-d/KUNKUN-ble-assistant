# -*- coding: utf-8 -*-
"""帮助菜单回归: 更新历史含各版本内容, 关于带可点击 GitHub 链接。"""
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

captured = {}


def fake_information(parent, title, text, *a, **k):
    captured["history"] = (title, text)


# 拦掉模态框, 只取内容(每次覆盖, 便于中英各验一次)
def fake_exec(self):
    captured["about"] = self
    return 0


QtWidgets.QMessageBox.information = staticmethod(fake_information)
QtWidgets.QDialog.exec = fake_exec

# ---- 更新历史: 含 V1.1.1 与 V1.1(第一版) ----
w._show_history()
title, text = captured["history"]
assert title == "更新历史", title
assert "V1.1.1" in text and "V1.1 (2026.10.17)" in text, text
assert "第一版" in text, text

# ---- 关于: GitHub 链接可点击跳转仓库, 有确定按钮 ----
w._show_about()
about = captured["about"]
links = [l for l in about.findChildren(QtWidgets.QLabel) if "href" in l.text()]
assert links, "关于对话框缺少链接"
link = links[0]
assert appmod.GITHUB_URL in link.text(), link.text()
assert link.openExternalLinks(), "链接未开启外部打开"
assert link.textFormat() == QtCore.Qt.RichText
assert any(b.text() == "确定" for b in about.findChildren(QtWidgets.QPushButton))

# ---- 英文界面: 历史内容与菜单词切换 ----
w._set_language("en")
qapp.processEvents()
w._show_history()
assert "First release" in captured["history"][1], captured["history"][1]
w._show_about()
about = captured["about"]
assert any(b.text() == "OK" for b in about.findChildren(QtWidgets.QPushButton))

print("HISTORY/ABOUT PASS")
