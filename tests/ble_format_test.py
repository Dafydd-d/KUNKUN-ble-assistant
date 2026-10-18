# -*- coding: utf-8 -*-
"""收发显示格式化回归: 控制字节/不可解字节转 \\xNN, 不再出现替换符乱码。"""
import os
import sys

proj = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, proj)
os.chdir(proj)

from ble_engine import build_data, format_bytes

# ---- 控制字节转义(乱码根因: \x01 等被当字符显示成方框/空) ----
assert format_bytes(b"\x01", "ascii") == "\\x01"
assert format_bytes(b"A\x00B\x7F", "ascii") == "A\\x00B\\x7F"
assert format_bytes(b"OK\r\n", "ascii") == "OK\\r\\n"
assert format_bytes(b"a\tb", "ascii") == "a\\tb"

# ---- UTF-8 正常文本与 HEX ----
assert format_bytes("温度:25℃".encode("utf-8"), "ascii") == "温度:25℃"
assert format_bytes("测A".encode("utf-8") + b"\x02", "ascii") == "测A\\x02"
assert format_bytes(b"hello", "hex") == "68 65 6C 6C 6F"

# ---- GBK 中文按编码解出 ----
assert format_bytes("你好".encode("gbk"), "ascii", "gbk") == "你好"
assert format_bytes("温".encode("gbk"), "mixed", "gbk") == "CE C2  |  温"

# ---- 编码不匹配时逐字节转义, 严禁出现 U+FFFD 替换符 ----
s = format_bytes("你好".encode("gbk"), "ascii", "utf-8")
assert s == "\\xC4\\xE3\\xBA\\xC3", s
assert "�" not in s
assert "�" not in format_bytes(b"OK\xe4\xb8", "ascii")
assert format_bytes(b"OK\xe4\xb8", "ascii") == "OK\\xE4\\xB8"  # 断尾多字节也转义

# ---- 混合模式与纯转义模式 ----
assert format_bytes(b"\x01\x02", "mixed") == "01 02  |  \\x01\\x02"
assert format_bytes(b"\x01A\x02", "ascii", "escape") == "\\x01A\\x02"
assert format_bytes("温".encode("gbk"), "ascii", "escape") == "\\xCE\\xC2"

# ---- 发送构造不回归 ----
assert build_data({"cmd": "AA 55", "fmt": "hex"}) == b"\xaa\x55"
assert build_data({"cmd": "hi", "fmt": "ascii", "line": "\r\n"}) == b"hi\r\n"
assert build_data({"cmd": "你好", "fmt": "ascii", "encoding": "gbk"}) == "你好".encode("gbk")

print("FORMAT PASS")
