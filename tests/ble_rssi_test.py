# -*- coding: utf-8 -*-
"""验证 RSSI 占位符不显示为数字, 保留最后一次真实测量。"""
import os
import sys

proj = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, proj)
os.chdir(proj)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets
import ble_serial_assistant as appmod

qapp = QtWidgets.QApplication(sys.argv[:1])
tok = appmod.THEMES["light"]

card = appmod.DeviceCard("AA", "X", -127, tok)   # 从未有真实测量
assert card.rssi_lbl.text() == "--", card.rssi_lbl.text()
card.set_rssi(-34)
assert card.rssi_lbl.text() == "-34"
card.set_rssi(-127)                              # 占位符不改写显示
assert card.rssi_lbl.text() == "-34", card.rssi_lbl.text()
card.set_rssi(None)
assert card.rssi_lbl.text() == "-34"
card.set_rssi(-42)                               # 新的真实测量会更新
assert card.rssi_lbl.text() == "-42"

card2 = appmod.DeviceCard("BB", "Y", -42, tok)
assert card2.rssi_lbl.text() == "-42"
card2.set_rssi(127)
assert card2.rssi_lbl.text() == "-42"

print("RSSI PASS")
