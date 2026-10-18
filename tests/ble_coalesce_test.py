# -*- coding: utf-8 -*-
"""接收拼包回归: 一帧被 BLE 通知拆成多包时合并为一行显示。"""
import os
import sys

proj = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, proj)
os.chdir(proj)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

import ble_serial_assistant as appmod

appmod.MainWindow._start_scan = lambda self: None
appmod.MainWindow._save_config = lambda self: None

qapp = QtWidgets.QApplication(sys.argv[:1])
w = appmod.MainWindow()
w.show()
qapp.processEvents()
w.seg_mode.set_value("hex")
w.edit_coalesce.setText("150")

H1 = bytes([0x3A, 0x7E, 0x01, 0x01])   # 帧前半(截图场景)
H2 = bytes([0x35, 0x14, 0x00])         # 帧后半, 与前半相隔约 96ms

# ---- 超时时间可手动输入, 乱输入按 0 ----
assert w._coalesce_ms() == 150
w.edit_coalesce.setText("abc")
assert w._coalesce_ms() == 0
w.edit_coalesce.setText("150")

# ---- 静默间隙内的两包合并为一帧, 时间戳取首字节 ----
w._on_rx(H1, 100.0)
w._on_rx(H2, 100.096)
assert w.receive_lines == [], w.receive_lines
assert bytes(w._rx_buf) == H1 + H2
assert w._t_rx_flush.isActive() and w._t_rx_flush.interval() == 150
w._flush_rx_frame()   # 模拟静默到点
assert w.receive_lines == ["[%s] RX: 3A 7E 01 01 35 14 00" % w._ts(100.0)], w.receive_lines
assert not w._rx_buf and not w._t_rx_flush.isActive()

# ---- 超时时间=0: 每包一行(旧行为) ----
w.edit_coalesce.setText("0")
w._on_rx(H1, 200.0)
w._on_rx(H2, 200.1)
assert len(w.receive_lines) == 3, w.receive_lines
assert w.receive_lines[1].endswith("RX: 3A 7E 01 01")
assert w.receive_lines[2].endswith("RX: 35 14 00")

# ---- 改回 0 时把已缓冲的帧放出来 ----
w.edit_coalesce.setText("150")
w._on_rx(H1, 300.0)
assert len(w.receive_lines) == 3
w.edit_coalesce.setText("0")   # textChanged -> 冲刷
assert len(w.receive_lines) == 4 and w.receive_lines[3].endswith("RX: 3A 7E 01 01")

# ---- 清空丢弃缓冲 ----
w.edit_coalesce.setText("150")
w._on_rx(H1, 400.0)
w._on_clear()
assert w.receive_lines == [] and not w._rx_buf and not w._t_rx_flush.isActive()

# ---- 切显示模式时冲刷缓冲 ----
w.seg_mode.set_value("ascii")
w._on_rx(bytes([0x4F, 0x4B]), 500.0)          # "OK"
w.seg_mode._buttons["hex"].click()            # 用户点 HEX -> 冲刷
assert len(w.receive_lines) == 1 and w.receive_lines[0].endswith("RX: 4F 4B"), w.receive_lines

# ---- 断开时冲刷缓冲 ----
w._on_rx(H2, 600.0)
w._on_conn_state("idle")
assert len(w.receive_lines) == 2 and w.receive_lines[1].endswith("RX: 35 14 00")

# ---- 上限阀门: 单包超长立即显示, 首尾相隔超 2s 也强制冲刷 ----
w._on_rx(bytes(1024), 700.0)
assert len(w.receive_lines) == 3, w.receive_lines          # 未扣住, 已合并显示
w._on_rx(bytes([0x41]), 800.0)
w._on_rx(bytes([0x42]), 803.0)                             # 帧龄超 RX_COALESCE_MAX_HOLD
assert len(w.receive_lines) == 4 and w.receive_lines[3].endswith("RX: 41 42"), w.receive_lines

print("COALESCE PASS")
