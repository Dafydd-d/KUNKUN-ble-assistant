#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
坤坤蓝牙助手 (Qt 版)
========================================================================
电脑蓝牙(BLE) <-> 透传模块(如 HC-04 / HM-10 / AT-09 / JDY-23 等) <-> MCU
的无线串口调试工具。界面基于 PySide6(Qt), 收发数据链路见 ble_engine.py。

功能:
    - 启动即持续自动扫描(无需按钮, 意外停止自动重试)
    - 自动识别常见透传服务: HC-04/HM-10(FFE0/FFE1) / Nordic UART(NUS) / ISSC;
      自定义 UUID 自动挑选收发特征, 也可手动指定(特征选择带自愈兜底)
    - 接收显示: ASCII / HEX / 混合, 带毫秒时间戳; 发送: ASCII/HEX, 可选行尾
    - 定时发送(轮询)、8 个预设命令、收发统计、自动/手动保存日志
    - 双主题: 浅色「仪器工作台」/ 深色「电台面板」, 菜单【工具】一键热切换

运行: python ble_serial_assistant.py    (或双击 启动.bat)
依赖: pip install -r requirements.txt   (pyside6 + bleak)
"""

import html
import json
import os
import sys
import time

from PySide6 import QtCore, QtGui, QtWidgets

from ble_engine import BleEngine, build_data, format_bytes, KNOWN_UUIDS
from i18n import tr, get_lang, set_lang

APP_NAME = "坤坤蓝牙助手"
APP_VERSION = "1.1"

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "ble_serial_config.json")
LOG_DIR = os.path.join(BASE_DIR, "logs")


def resource_path(name):
    bundle_dir = getattr(sys, "_MEIPASS", BASE_DIR)
    return os.path.join(bundle_dir, name)


def ui_font(size=10):
    f = QtGui.QFont()
    f.setFamilies(["Microsoft YaHei UI", "Microsoft YaHei", "SimHei", "sans-serif"])
    f.setPointSize(size)
    return f


def mono_font(size=10):
    f = QtGui.QFont()
    # 末尾几个是缺字回退: 设备发来 emoji/图形符号时不要显示成方框
    f.setFamilies(["Consolas", "Courier New", "Segoe UI Emoji", "Segoe UI Symbol",
                   "Microsoft YaHei UI", "monospace"])
    f.setPointSize(size)
    return f


# 接收区行数上限(超出从顶部裁掉旧内容; 完整记录仍保留在内存/日志中)
RECV_MAX_LINES = 4000
RECV_TRIM_TO = 3000

# 拼包: 一帧被 BLE 通知拆成多包时合并显示; 静默间隙由界面「拼包」设置,
# 上限防止持续细流把数据一直扣着不显示
RX_COALESCE_MAX_BYTES = 1024
RX_COALESCE_MAX_HOLD = 2.0

# 设备列表清理: 超过该秒数没再广播的设备从列表移除(连接中的保留)
DEV_STALE_SEC = 10

# ---------------------------------------------------------------------------
# 双主题设计令牌: 浅色=「仪器工作台」 深色=「电台面板」
# ---------------------------------------------------------------------------
THEMES = {
    "light": {
        "TITLE_FG": "#FFFFFF", "VER_FG": "#7FA3B8", "HEADER_BG": "#14314B",
        "INK": "#14314B", "BG": "#E9EDF0", "PANEL": "#FFFFFF", "FG": "#1F2937",
        "ACCENT": "#0E7490", "ACCENT_D": "#0C5D73", "SEL_FG": "#FFFFFF",
        "MUTED": "#5C6B78", "BORDER": "#C9D3DA", "ARROW": "arrow_down.png",
        "POPUP_SEL_BG": "#CFE6EE", "POPUP_SEL_FG": "#14314B",
        "BTN_BG": "#DFE5EA", "BTN_BG_HOVER": "#CBD6DD",
        "BTN_DIS_BG": "#E8EDF0", "BTN_DIS_FG": "#9AA7B1",
        "SEG_REST_BG": "#D5DEE4", "SEG_REST_FG": "#334552",
        "SEG_BORDER": "#B7C3CC",
        "PILL_BG": "#1C4358", "PILL_FG": "#FFFFFF", "PILL_DIV": "#2F5D7A",
        "PILL_DEV_FG": "#A9C4D4",
        "HBTN_BG": "#24506E", "HBTN_BG_HOVER": "#2E6185",
        "HBTN_FG": "#FFFFFF", "HBTN_DIS_FG": "#6E8BA0",
        "SCREEN": "#0C1E2A", "SCREEN_HDR": "#102B3C", "SCREEN_LINE": "#21445B",
        "SCREEN_FG": "#D7E9F2", "SCREEN_TX": "#5EEAD4", "SCREEN_DIM": "#8FB3C7",
        "SCREEN_WARN": "#FBBF24", "SCREEN_ERR": "#F87171",
        "SCREEN_LABEL": "#9FBDCF", "RO_LABEL": "#6E93A8",
        "DBTN_BG": "#1B3A4E", "DBTN_BG_HOVER": "#26506B", "DBTN_FG": "#D7E9F2",
        "ICON_BG": "#0E7490", "ICON_FG": "#FFFFFF",
        "OK_GREEN": "#22C55E", "WARN_AMBER": "#F59E0B", "IDLE_GRAY": "#9AA7B1",
        "CARD_BG": "#FFFFFF", "CARD_BG_ALT": "#F3F6F8",
        "CARD_BORDER": "#C9D3DA", "CARD_BORDER_SEL": "#0E7490",
        "NAME_FG": "#14314B", "ADDR_FG": "#5C6B78",
    },
    "dark": {
        "TITLE_FG": "#ECE7D9", "VER_FG": "#7A7466", "HEADER_BG": "#1A1D21",
        "INK": "#ECE7D9", "BG": "#23272C", "PANEL": "#1A1D21", "FG": "#C9C4B6",
        "ACCENT": "#E8B33A", "ACCENT_D": "#D19E2E", "SEL_FG": "#1A1D21",
        "MUTED": "#9A927F", "BORDER": "#3A3F46", "ARROW": "arrow_down_dark.png",
        "POPUP_SEL_BG": "#2E4A57", "POPUP_SEL_FG": "#ECE7D9",
        "BTN_BG": "#3A3F46", "BTN_BG_HOVER": "#4A5058",
        "BTN_DIS_BG": "#2F343A", "BTN_DIS_FG": "#6A6458",
        "SEG_REST_BG": "#2A2E34", "SEG_REST_FG": "#B0A894",
        "SEG_BORDER": "#4A5058",
        "PILL_BG": "#1A1D21", "PILL_FG": "#ECE7D9", "PILL_DIV": "#3A3F46",
        "PILL_DEV_FG": "#9A927F",
        "HBTN_BG": "#3A3F46", "HBTN_BG_HOVER": "#4A5058",
        "HBTN_FG": "#C9C4B6", "HBTN_DIS_FG": "#6A6458",
        "SCREEN": "#14161A", "SCREEN_HDR": "#1E2126", "SCREEN_LINE": "#2A2E34",
        "SCREEN_FG": "#FFB454", "SCREEN_TX": "#8FD98F", "SCREEN_DIM": "#8A8272",
        "SCREEN_WARN": "#FBBF24", "SCREEN_ERR": "#F87171",
        "SCREEN_LABEL": "#E8B33A", "RO_LABEL": "#8F887A",
        "DBTN_BG": "#2A2E34", "DBTN_BG_HOVER": "#3A3F46", "DBTN_FG": "#C9C4B6",
        "ICON_BG": "#3A3F46", "ICON_FG": "#FFFFFF",
        "OK_GREEN": "#22C55E", "WARN_AMBER": "#F59E0B", "IDLE_GRAY": "#9AA7B1",
        "CARD_BG": "#2A2E34", "CARD_BG_ALT": "#262A2F",
        "CARD_BORDER": "#343940", "CARD_BORDER_SEL": "#E8B33A",
        "NAME_FG": "#ECE7D9", "ADDR_FG": "#8F887A",
    },
}


def build_qss(t):
    """由令牌生成整套样式表; 结构只此一份, 两套主题换色不换骨。"""
    arrow = resource_path(t.get("ARROW", "arrow_down.png")).replace("\\", "/")
    return """
QWidget {{ background: {BG}; color: {FG}; }}
QMainWindow::separator {{ background: {BORDER}; }}

/* ---- 顶部链路仪表条 ---- */
QFrame#header {{ background: {HEADER_BG}; }}
QFrame#header QLabel {{ background: transparent; }}
QLabel#brand    {{ color: {TITLE_FG}; font-size: 13pt; font-weight: bold; background: transparent; }}
QLabel#brandVer {{ color: {VER_FG}; font-size: 9pt; background: transparent; }}
QFrame#pill {{ background: {PILL_BG}; border-radius: 3px; }}
QLabel#pillState {{ color: {PILL_FG}; font-weight: bold; background: transparent; }}
QLabel#pillDev   {{ color: {PILL_DEV_FG}; background: transparent; font-size: 9pt;
                   selection-background-color: {ACCENT}; selection-color: {SEL_FG}; }}
QFrame#pillDiv {{ background: {PILL_DIV}; }}
QPushButton#hbtn {{ background: {HBTN_BG}; color: {HBTN_FG}; border: none;
                    padding: 5px 14px; border-radius: 3px; }}
QPushButton#hbtn:hover {{ background: {HBTN_BG_HOVER}; }}
QPushButton#hbtn:disabled {{ color: {HBTN_DIS_FG}; }}

/* ---- 分区标题 ---- */
QLabel#secTitle {{ color: {INK}; font-size: 10.5pt; font-weight: bold; background: transparent; }}
QLabel#secHint  {{ color: {MUTED}; font-size: 8.5pt; background: transparent; }}
QFrame#secLine  {{ background: {BORDER}; max-height: 1px; }}

/* ---- 设备卡片 ---- */
QScrollArea#devScroll {{ border: none; background: transparent; }}
QFrame#card {{ background: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: 4px; }}
QFrame#card[sel="true"] {{ border: 1px solid {CARD_BORDER_SEL}; }}
QFrame#card:hover {{ border: 1px solid {CARD_BORDER_SEL}; }}
QLabel#cardName {{ color: {NAME_FG}; font-weight: bold; background: transparent; }}
QLabel#cardAddr {{ color: {ADDR_FG}; font-size: 8.5pt; background: transparent; }}
QLabel#cardRssi {{ color: {ADDR_FG}; background: transparent; }}
QPushButton#connBtn {{ background: {ACCENT}; color: {SEL_FG}; border: none;
                        padding: 4px 14px; border-radius: 3px; font-size: 9pt; }}
QPushButton#connBtn:hover {{ background: {ACCENT_D}; }}
QPushButton#connBtn:disabled {{ background: {BTN_DIS_BG}; color: {BTN_DIS_FG}; }}

/* ---- 表单控件 ---- */
QLineEdit, QPlainTextEdit#sendText, QTextEdit#sendText {{
    background: {PANEL}; color: {FG}; border: 1px solid {BORDER};
    border-radius: 3px; padding: 3px 6px; selection-background-color: {ACCENT};
    selection-color: {SEL_FG}; }}
/* 下拉都是非编辑型, selection-* 只作用于弹出列表的选中行(浅色高亮);
   注意: 此处纵向 padding 会泄漏进弹层容器几何(顶出白条), 只能给 1px */
QComboBox {{
    background: {PANEL}; color: {FG}; border: 1px solid {BORDER};
    border-radius: 3px; padding: 1px 6px;
    selection-background-color: {POPUP_SEL_BG}; selection-color: {POPUP_SEL_FG}; }}
QLineEdit:focus, QComboBox:focus, QTextEdit#sendText:focus {{ border: 1px solid {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{ image: url({ARROW}); width: 10px; height: 7px; }}
QComboBox QAbstractItemView {{ background: {PANEL}; color: {FG};
                               border: 1px solid {BORDER}; outline: none;
                               selection-background-color: {POPUP_SEL_BG};
                               selection-color: {POPUP_SEL_FG}; }}
/* 弹层外层容器自带双线边框/空隙, 去掉让列表像系统下拉一样干净 */
QComboBoxPrivateContainer {{ border: none; background: {PANEL}; margin: 0; padding: 0; }}
QComboBox QFrame {{ border: none; background: {PANEL}; margin: 0; padding: 0; }}

/* ---- 按钮 ---- */
QPushButton {{ background: {BTN_BG}; color: {FG}; border: none;
               padding: 6px 14px; border-radius: 3px; }}
QPushButton:hover {{ background: {BTN_BG_HOVER}; }}
QPushButton:disabled {{ background: {BTN_DIS_BG}; color: {BTN_DIS_FG}; }}
QPushButton#accentBtn {{ background: {ACCENT}; color: {SEL_FG}; font-weight: bold; }}
QPushButton#accentBtn:hover {{ background: {ACCENT_D}; }}
QPushButton#accentBtn:disabled {{ background: {BTN_DIS_BG}; color: {BTN_DIS_FG}; }}
QPushButton#sendBtn {{ background: {ACCENT}; color: {SEL_FG}; font-size: 12pt;
                       font-weight: bold; padding: 12px 26px; border-radius: 4px; }}
QPushButton#sendBtn:hover {{ background: {ACCENT_D}; }}
QPushButton#sendBtn:disabled {{ background: {BTN_DIS_BG}; color: {BTN_DIS_FG}; }}
QPushButton#miniBtn {{ padding: 3px 12px; }}

/* ---- 服务树 ---- */
QTreeWidget {{ background: {PANEL}; color: {FG}; border: 1px solid {BORDER};
               border-radius: 3px; }}
QTreeWidget::item {{ padding: 3px 4px; }}
QTreeWidget::item:selected {{ background: {ACCENT}; color: {SEL_FG}; }}
QHeaderView::section {{ background: {BTN_BG}; color: {FG}; border: none;
                        padding: 4px 6px; font-weight: bold; }}

/* ---- 仪表屏(接收监视) ---- */
QFrame#screen {{ background: {SCREEN}; border-radius: 4px; }}
QFrame#screenStrip {{ background: {SCREEN_HDR}; border: none; }}
QFrame#screenLine {{ background: {SCREEN_LINE}; max-height: 1px; }}
QLabel#screenLabel {{ color: {SCREEN_LABEL}; font-weight: bold; background: transparent; }}
QLabel#roLabel {{ color: {RO_LABEL}; background: transparent; font-size: 8.5pt; }}
QLabel#roValue {{ color: {SCREEN_FG}; background: transparent;
                  font-family: Consolas, monospace; font-size: 9.5pt; font-weight: bold; }}
QTextEdit#recvText {{ background: {SCREEN}; color: {SCREEN_FG}; border: none;
                      selection-background-color: {ACCENT}; selection-color: {SEL_FG};
                      padding: 6px; }}
QPushButton#dbtn {{ background: {DBTN_BG}; color: {DBTN_FG}; border: none;
                    padding: 4px 12px; border-radius: 3px; font-size: 9pt; }}
QPushButton#dbtn:hover {{ background: {DBTN_BG_HOVER}; }}

/* ---- 分段控件(浅色台面变体; 深色屏变体见 #segWrapDark) ---- */
QToolButton[seg="true"] {{ background: {SEG_REST_BG}; color: {SEG_REST_FG};
                          border: 1px solid {SEG_BORDER}; padding: 4px 14px; }}
QToolButton[seg="true"]:checked {{ background: {ACCENT}; color: {SEL_FG};
                                   border: 1px solid {ACCENT}; font-weight: bold; }}
QToolButton[seg="true"]:hover:!checked {{ background: {BTN_BG_HOVER}; }}
#segWrapDark QToolButton[seg="true"] {{ background: {SCREEN_HDR}; color: {SCREEN_DIM};
                                       border: 1px solid {SCREEN_LINE}; }}
#segWrapDark QToolButton[seg="true"]:checked {{ background: {ACCENT}; color: {SEL_FG};
                                                border: 1px solid {ACCENT}; }}
#segWrapDark QToolButton[seg="true"]:hover:!checked {{ background: {SCREEN_LINE}; }}

/* ---- 底部读数条 ---- */
QFrame#statusbar {{ background: {PANEL}; border-top: 1px solid {BORDER}; }}
QLabel#gLabel {{ color: {MUTED}; background: transparent; font-size: 8.5pt; }}
QLabel#gValue {{ color: {INK}; background: transparent;
                 font-weight: bold; }}
QFrame#hair {{ background: {BORDER}; max-width: 1px; }}

/* ---- 滚动条 / 分隔条 ---- */
QScrollBar:vertical {{ background: {BG}; width: 12px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {BTN_BG_HOVER}; border-radius: 4px;
                               min-height: 24px; margin: 2px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: {BG}; height: 12px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: {BTN_BG_HOVER}; border-radius: 4px;
                                 min-width: 24px; margin: 2px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QSplitter::handle {{ background: {BORDER}; width: 5px; }}
QMenuBar {{ background: {BG}; color: {FG}; }}
QMenuBar::item:selected {{ background: {BTN_BG_HOVER}; }}
QMenu {{ background: {PANEL}; color: {FG}; border: 1px solid {BORDER}; }}
QMenu::item:selected {{ background: {ACCENT}; color: {SEL_FG}; }}
QToolTip {{ background: {PANEL}; color: {FG}; border: 1px solid {BORDER}; }}
""".format(**{**t, "ARROW": arrow})


# ---------------------------------------------------------------------------
# 小部件
# ---------------------------------------------------------------------------
class AnchoredCombo(QtWidgets.QComboBox):
    """下拉弹层锚定: 当前选中项永远是列表首行, 列表贴框向下展开。

    选项不出现在当前选择的上方——打开时把当前项转到首行
    (其余选项按原序循环跟随), 弹层左上角对齐到框的左上角。"""

    def showPopup(self):
        self._move_current_to_top()
        super().showPopup()
        cont = self.view().parentWidget()
        if cont is not None:
            cont.move(self.mapToGlobal(QtCore.QPoint(0, 0)))

    def _move_current_to_top(self):
        idx, n = self.currentIndex(), self.count()
        if idx <= 0 or n <= 1:
            return
        items = [(self.itemText(i), self.itemData(i)) for i in range(n)]
        self.blockSignals(True)
        try:
            self.clear()
            for text, data in items[idx:] + items[:idx]:
                self.addItem(text, data)
            self.setCurrentIndex(0)
        finally:
            self.blockSignals(False)


class PopupItemDelegate(QtWidgets.QStyledItemDelegate):
    """下拉弹层条目: 8pt 小字号 + 紧凑行高, 贴近系统下拉列表观感。

    条目级 QSS(::item)在当前 Qt 上不生效, 行高/字号只能在委托里控制。"""

    @staticmethod
    def _font(option):
        f = QtGui.QFont(option.font)
        f.setPointSize(8)
        return f

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        option.font = self._font(option)

    def sizeHint(self, option, index):
        s = super().sizeHint(option, index)
        s.setHeight(max(22, QtGui.QFontMetrics(self._font(option)).height() + 6))
        return s


def apply_popup_style(cb):
    cb.setItemDelegate(PopupItemDelegate(cb))
    view = cb.view()
    view.setUniformItemSizes(True)
    f = QtGui.QFont(view.font())
    f.setPointSize(8)
    view.setFont(f)
    # 弹层外层容器自带双线边框和空隙(QSS 改不动), 直接清掉
    cont = view.parentWidget()
    if isinstance(cont, QtWidgets.QFrame):
        cont.setFrameShape(QtWidgets.QFrame.NoFrame)
        cont.setContentsMargins(0, 0, 0, 0)
        lay = cont.layout()
        if lay is not None:
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(0)


class EventBridge(QtCore.QObject):
    """引擎线程 -> Qt 主线程的事件桥(信号跨线程自动排队)。"""
    got = QtCore.Signal(object)


class BtIcon(QtWidgets.QWidget):
    """强调色圆底 + 蓝牙符文。
    字形用 Windows 自带 Segoe MDL2 Assets 的官方 Bluetooth 图标(U+E702),
    按字形实际度量居中; 无该字体的环境退化为描边折线。"""

    _HAS_MDL2 = None   # 字体可用性缓存

    def __init__(self, tok, size=26, parent=None):
        super().__init__(parent)
        self.tok = tok
        self.setFixedSize(size, size)
        if BtIcon._HAS_MDL2 is None:
            BtIcon._HAS_MDL2 = "Segoe MDL2 Assets" in QtGui.QFontDatabase.families()

    def set_theme(self, tok):
        self.tok = tok
        self.update()

    def paintEvent(self, ev):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        s = min(self.width(), self.height())
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(self.tok["ICON_BG"]))
        p.drawEllipse(0, 0, s - 1, s - 1)
        fg = QtGui.QColor(self.tok["ICON_FG"])
        if BtIcon._HAS_MDL2:
            f = QtGui.QFont("Segoe MDL2 Assets")
            f.setPixelSize(max(8, int(s * 0.62)))
            p.setFont(f)
            p.setPen(fg)
            fm = QtGui.QFontMetrics(f)
            br = fm.tightBoundingRect("")
            x = (s - br.width()) / 2.0 - br.left()
            y = (s - br.height()) / 2.0 - br.top()
            p.drawText(QtCore.QPointF(x, y), "")
            return
        # 兜底: 描边折线
        pen = QtGui.QPen(fg)
        pen.setWidthF(max(1.6, s * 0.075))
        pen.setCapStyle(QtCore.Qt.FlatCap)
        pen.setJoinStyle(QtCore.Qt.RoundJoin)
        p.setPen(pen)
        k = s / 26.0
        pts = [QtCore.QPointF(9 * k, 6 * k), QtCore.QPointF(17 * k, 9.5 * k),
               QtCore.QPointF(9 * k, 13 * k), QtCore.QPointF(17 * k, 16.5 * k),
               QtCore.QPointF(9 * k, 20 * k)]
        p.drawLine(QtCore.QPointF(9 * k, 6 * k), QtCore.QPointF(9 * k, 20 * k))
        p.drawPolyline(QtGui.QPolygonF(pts))


class SignalBars(QtWidgets.QWidget):
    """4 格信号强度指示。"""

    def __init__(self, tok, parent=None):
        super().__init__(parent)
        self.tok = tok
        self.level = 0
        self.setFixedSize(20, 12)

    def set_theme(self, tok):
        self.tok = tok
        self.update()

    def set_level(self, level):
        if level != self.level:
            self.level = level
            self.update()

    def paintEvent(self, ev):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        on = QtGui.QColor(self.tok["ACCENT"])
        off = QtGui.QColor(self.tok["CARD_BORDER"])
        for i, h in enumerate((4, 6, 8, 10)):
            p.fillRect(1 + i * 5, 11 - h, 3, h, on if i < self.level else off)


class ToggleSwitch(QtWidgets.QWidget):
    """滑动开关(替代复选框): 轨道+滑块, 开=强调色, 带轻量滑动动画。"""
    toggled = QtCore.Signal(bool)

    def __init__(self, text, tok, checked=False, parent=None):
        super().__init__(parent)
        self.tok = tok
        self._checked = checked
        self._pos = 1.0 if checked else 0.0
        self._anim = None
        self._label = text
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.TabFocus)
        self.setAttribute(QtCore.Qt.WA_Hover, True)

    # --- Qt 兼容 API(与 QCheckBox 一致) ---
    def isChecked(self):
        return self._checked

    def setChecked(self, v):
        v = bool(v)
        if v == self._checked:
            return
        self._checked = v
        self._animate()
        self.toggled.emit(v)

    def set_theme(self, tok):
        self.tok = tok
        self.update()

    def set_label(self, text):
        self._label = text
        self.update()

    # --- 交互 ---
    def mousePressEvent(self, ev):
        self.setChecked(not self._checked)

    def keyPressEvent(self, ev):
        if ev.key() in (QtCore.Qt.Key_Space, QtCore.Qt.Key_Return):
            self.setChecked(not self._checked)
        else:
            super().keyPressEvent(ev)

    def sizeHint(self):
        fm = self.fontMetrics()
        return QtCore.QSize(fm.horizontalAdvance(self._label) + 42, 24)

    def _animate(self):
        target = 1.0 if self._checked else 0.0
        if self._anim is not None:
            self._anim.stop()
        anim = QtCore.QVariantAnimation(self, duration=120)
        anim.setStartValue(self._pos)
        anim.setEndValue(target)
        anim.valueChanged.connect(self._on_anim)
        anim.start()
        self._anim = anim

    def _on_anim(self, v):
        self._pos = float(v)
        self.update()

    def paintEvent(self, ev):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        h = self.height()
        tw, th = 30, 16
        ty = (h - th) / 2
        # 轨道
        track_on = QtGui.QColor(self.tok["ACCENT"])
        track_off = QtGui.QColor(self.tok["SCREEN_LINE"])

        # 手动按 pos 混合两色
        def mix(a, b, t):
            return QtGui.QColor(int(a.red() + (b.red() - a.red()) * t),
                                int(a.green() + (b.green() - a.green()) * t),
                                int(a.blue() + (b.blue() - a.blue()) * t))
        c = mix(track_off, track_on, self._pos)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(c)
        p.drawRoundedRect(QtCore.QRectF(0, ty, tw, th), th / 2, th / 2)
        # 滑块
        d = 12
        x = 2 + self._pos * (tw - d - 4)
        knob = QtGui.QColor(self.tok["SEL_FG"])
        p.setBrush(knob)
        p.drawEllipse(QtCore.QPointF(x + d / 2, ty + th / 2), d / 2, d / 2)
        # 文本(开=高亮)
        label_color = QtGui.QColor(
            self.tok["SCREEN_FG"] if self._checked else self.tok["SCREEN_DIM"])
        p.setPen(label_color)
        p.setFont(self.font())
        p.drawText(QtCore.QRectF(tw + 8, 0, self.width() - tw - 8, h),
                   QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, self._label)


class Segmented(QtWidgets.QWidget):
    """扁平分段控件: 一组互斥按钮, 选中为强调色。"""
    changed = QtCore.Signal(str)

    def __init__(self, options, value="", dark=False, parent=None):
        super().__init__(parent)
        # 深色屏变体用独立 objectName 匹配样式(属性选择器曾因类型不匹配而失效)
        self.setObjectName("segWrapDark" if dark else "segWrap")
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(1)
        self._group = QtWidgets.QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons = {}
        for key, text in options:
            btn = QtWidgets.QToolButton()
            btn.setText(text)
            btn.setProperty("seg", "true")
            btn.setProperty("key", key)
            btn.setCheckable(True)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            self._group.addButton(btn)
            self._buttons[key] = btn
            lay.addWidget(btn)
            btn.clicked.connect(lambda _=False, k=key: self.changed.emit(k))
        self.set_value(value)

    def value(self):
        btn = self._group.checkedButton()
        return btn.property("key") if btn is not None else ""

    def set_value(self, key):
        btn = self._buttons.get(key)
        if btn is not None:
            btn.setChecked(True)

    def set_option_text(self, key, text):
        btn = self._buttons.get(key)
        if btn is not None:
            btn.setText(text)


class DeviceCard(QtWidgets.QFrame):
    """设备卡片: 图标 / 名称地址 / 信号 / 连接按钮。"""
    connect_clicked = QtCore.Signal(str)
    selected = QtCore.Signal(str)
    double_clicked = QtCore.Signal(str)

    def __init__(self, address, name, rssi, tok, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.address = address
        self.tok = tok
        self._last_rssi = None
        self.setCursor(QtCore.Qt.PointingHandCursor)
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(10)
        self.icon = BtIcon(tok)
        lay.addWidget(self.icon)
        mid = QtWidgets.QVBoxLayout()
        mid.setSpacing(1)
        self.name_lbl = QtWidgets.QLabel(name)
        self.name_lbl.setObjectName("cardName")
        self.addr_lbl = QtWidgets.QLabel(address)
        self.addr_lbl.setObjectName("cardAddr")
        self.addr_lbl.setFont(mono_font(8))
        mid.addWidget(self.name_lbl)
        mid.addWidget(self.addr_lbl)
        lay.addLayout(mid, 1)
        right = QtWidgets.QVBoxLayout()
        right.setSpacing(5)
        sig = QtWidgets.QHBoxLayout()
        sig.setSpacing(5)
        self.bars = SignalBars(tok)
        self.rssi_lbl = QtWidgets.QLabel("--")
        self.rssi_lbl.setObjectName("cardRssi")
        self.rssi_lbl.setFixedWidth(34)
        self.rssi_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        sig.addWidget(self.bars)
        sig.addWidget(self.rssi_lbl)
        right.addLayout(sig)
        self.conn_btn = QtWidgets.QPushButton(tr("连接"))
        self.conn_btn.setObjectName("connBtn")
        self.conn_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.conn_btn.clicked.connect(lambda: self.connect_clicked.emit(self.address))
        right.addWidget(self.conn_btn, 0, QtCore.Qt.AlignRight)
        lay.addLayout(right)
        self.set_rssi(rssi)

    def set_theme(self, tok):
        self.tok = tok
        self.icon.set_theme(tok)
        self.bars.set_theme(tok)
        self._apply_rssi_color()

    def retranslate(self):
        self.conn_btn.setText(tr("连接"))

    def set_selected(self, sel):
        self.setProperty("sel", "true" if sel else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def set_rssi(self, rssi):
        # ±127 是 BLE "无测量值" 占位符(连接后/缓存事件常见), 只记录真实测量
        if rssi is not None and abs(rssi) < 127:
            self._last_rssi = rssi
        rssi = self._last_rssi
        self.rssi_lbl.setText("--" if rssi is None else "%d" % rssi)
        if rssi is None:
            level = 0
        elif rssi >= -55:
            level = 4
        elif rssi >= -67:
            level = 3
        elif rssi >= -80:
            level = 2
        else:
            level = 1
        self.bars.set_level(level)

    def _apply_rssi_color(self):
        pass

    def mousePressEvent(self, ev):
        self.selected.emit(self.address)
        super().mousePressEvent(ev)

    def mouseDoubleClickEvent(self, ev):
        self.double_clicked.emit(self.address)
        super().mouseDoubleClickEvent(ev)


class CopyableLabel(QtWidgets.QLabel):
    """可拖选复制的文本标签: 拖选后 Ctrl+C, 右键菜单, 双击整段复制。"""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.setCursor(QtGui.QCursor(QtCore.Qt.IBeamCursor))
        self.setToolTip(tr("点击拖动选中文字后 Ctrl+C 复制；双击一键复制；右键更多选项"))
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

    def mouseDoubleClickEvent(self, ev):
        if self.text() and self.text() != tr("未选择设备"):
            QtWidgets.QApplication.clipboard().setText(self.text())
            QtWidgets.QToolTip.showText(ev.globalPosition().toPoint(),
                                        tr("已复制: %s") % self.text(), self)
        ev.accept()

    def _on_context_menu(self, pos):
        menu = QtWidgets.QMenu(self)
        act_copy_sel = menu.addAction(tr("复制选中内容"))
        act_copy_sel.setEnabled(bool(self.selectedText()))
        act_copy_all = menu.addAction(tr("复制名称和 MAC"))
        chosen = menu.exec_(self.mapToGlobal(pos))
        if chosen is act_copy_sel:
            QtWidgets.QApplication.clipboard().setText(self.selectedText())
        elif chosen is act_copy_all:
            QtWidgets.QApplication.clipboard().setText(self.text())


# ---------------------------------------------------------------------------
# 主窗口
# ---------------------------------------------------------------------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("%s V%s" % (APP_NAME, APP_VERSION))
        self.resize(1180, 800)

        # ---- 主题(先于控件构建) ----
        self.theme_name = "light"
        cfg0 = self._peek_config()
        if cfg0.get("theme") in THEMES:
            self.theme_name = cfg0["theme"]
        self.tok = THEMES[self.theme_name]
        self.lang_name = "en" if cfg0.get("lang") == "en" else "zh"
        set_lang(self.lang_name)
        self._retrans = []              # 语言切换时重放的文案闭包

        # ---- 状态 ----
        self.conn_state = "idle"
        self.scanning = False
        self.rx_bytes = self.tx_bytes = self.rx_packets = 0
        self.receive_lines = []
        self.recv_tags = []
        self._pending_lines = []
        self._rx_buf = bytearray()      # 拼包缓冲: 静默间隙内的包合并为一帧
        self._rx_buf_ts = None          # 缓冲首字节到达时刻(帧时间戳)
        self._status_dirty = False
        self._pending_devices = {}      # address -> {"name", "rssi"} 广播合并
        self.devices = {}               # address -> {"name", "rssi"}
        self._recv_hint_visible = False
        self._conn_addr = None          # 正在连接/已连接的设备(与列表选中相互独立)
        self.cards = {}                 # address -> DeviceCard
        self.selected_addr = None
        self.char_options = []          # [(disp, uuid)]
        self._char_prefs = {}           # 地址 -> {"write","notify"} 手动指定记忆
        self._last_services = None
        self._last_uart_ev = None
        self._shutting_down = False
        self.auto_log_path = None
        self.auto_log_fp = None
        self._last_log_flush = 0.0
        self._periodic_running = False

        # ---- 引擎(独立线程) ----
        self.bridge = EventBridge()
        self.bridge.got.connect(self._on_event)     # 自动回到主线程
        self.engine = BleEngine(sink=self.bridge.got.emit)
        self.engine.start()

        # ---- 界面 ----
        self._build_ui()
        self._load_config(cfg0)

        # ---- 定时器 ----
        self._t_lines = QtCore.QTimer(self)
        self._t_lines.timeout.connect(self._flush_lines)
        self._t_lines.start(30)
        self._t_devs = QtCore.QTimer(self)
        self._t_devs.timeout.connect(self._flush_devices)
        self._t_devs.start(250)
        self._t_snap = QtCore.QTimer(self)
        self._t_snap.timeout.connect(self._periodic_snapshot)
        self._t_snap.start(50)
        self._t_log = QtCore.QTimer(self)
        self._t_log.timeout.connect(self._flush_log)
        self._t_log.start(1000)
        self._t_rx_flush = QtCore.QTimer(self)   # 拼包静默窗口, 到点合并显示
        self._t_rx_flush.setSingleShot(True)
        self._t_rx_flush.timeout.connect(self._flush_rx_frame)

        # 启动即持续扫描
        QtCore.QTimer.singleShot(300, self._start_scan)

    # ================= UI 构建 =================
    def _build_ui(self):
        central = QtWidgets.QWidget()
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- 顶部链路仪表条 ----
        header = QtWidgets.QFrame()
        header.setObjectName("header")
        hly = QtWidgets.QHBoxLayout(header)
        hly.setContentsMargins(14, 9, 12, 9)
        hly.setSpacing(10)
        icon = QtWidgets.QLabel()
        pm = QtGui.QPixmap(resource_path("app_icon.png"))
        if not pm.isNull():
            icon.setPixmap(pm.scaled(26, 26, QtCore.Qt.KeepAspectRatio,
                                     QtCore.Qt.SmoothTransformation))
        hly.addWidget(icon)
        brand = QtWidgets.QLabel(APP_NAME)
        brand.setObjectName("brand")
        hly.addWidget(brand)
        ver = QtWidgets.QLabel("V" + APP_VERSION)
        ver.setObjectName("brandVer")
        hly.addWidget(ver)

        pill = QtWidgets.QFrame()
        pill.setObjectName("pill")
        ply = QtWidgets.QHBoxLayout(pill)
        ply.setContentsMargins(12, 6, 12, 6)
        ply.setSpacing(9)
        self.pill_dot = QtWidgets.QLabel()
        self.pill_dot.setFixedSize(11, 11)
        ply.addWidget(self.pill_dot)
        self.pill_state = QtWidgets.QLabel(tr("未连接"))
        self.pill_state.setObjectName("pillState")
        ply.addWidget(self.pill_state)
        pdiv = QtWidgets.QFrame()
        pdiv.setObjectName("pillDiv")
        pdiv.setFixedWidth(1)
        ply.addWidget(pdiv)
        self.pill_dev = CopyableLabel(tr("未选择设备"))
        self.pill_dev.setObjectName("pillDev")
        ply.addWidget(self.pill_dev)
        hly.addWidget(pill)
        hly.addStretch(1)
        self.btn_disconnect = QtWidgets.QPushButton(tr("断开"))
        self.btn_disconnect.setObjectName("hbtn")
        self._reg(lambda: self.btn_disconnect.setText(tr("断开")))
        self.btn_disconnect.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_disconnect.setEnabled(False)
        self.btn_disconnect.clicked.connect(self._on_disconnect)
        hly.addWidget(self.btn_disconnect)
        root.addWidget(header)

        # ---- 主分割区 ----
        split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        split.setChildrenCollapsible(False)
        split.addWidget(self._build_left())
        split.addWidget(self._build_right())
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([400, 780])
        self.split = split
        root.addWidget(split, 1)

        # ---- 底部读数条 ----
        bar = QtWidgets.QFrame()
        bar.setObjectName("statusbar")
        bly = QtWidgets.QHBoxLayout(bar)
        bly.setContentsMargins(14, 5, 14, 5)
        bly.setSpacing(14)

        def cell(label_zh, ctx=""):
            f = QtWidgets.QHBoxLayout()
            f.setSpacing(6)
            lab = QtWidgets.QLabel(tr(label_zh, ctx))
            lab.setObjectName("gLabel")
            val = QtWidgets.QLabel("-")
            val.setObjectName("gValue")
            f.addWidget(lab)
            f.addWidget(val)
            self._reg(lambda: lab.setText(tr(label_zh, ctx)))
            return f, val

        # 底部只放链路遥测; 状态/设备已在顶部状态灯, 不再重复
        lay_m, self.g_mtu = cell("MTU")
        lay_r, self.g_rx = cell("接收", "bar")
        lay_t, self.g_tx = cell("发送", "bar")
        for i, lay in enumerate((lay_m, lay_r, lay_t)):
            bly.addLayout(lay)
            if i < 2:
                hair = QtWidgets.QFrame()
                hair.setObjectName("hair")
                hair.setFixedWidth(1)
                bly.addWidget(hair)
        bly.addStretch(1)
        root.addWidget(bar)

        self.setCentralWidget(central)
        self._build_menu()
        self._apply_theme_colors()

    def _reg(self, fn):
        """登记一条文案闭包(立即生效, 语言切换时重放)。"""
        self._retrans.append(fn)
        fn()

    def _set_language(self, name):
        name = "en" if name == "en" else "zh"
        self.lang_name = name
        set_lang(name)
        for fn in self._retrans:
            fn()
        for card in self.cards.values():
            card.retranslate()
        self._act_zh.setChecked(name == "zh")
        self._act_en.setChecked(name == "en")
        if self._last_services:
            self._on_services(self._last_services)
        self._update_status()
        self._update_recv_hint()
        self._save_config()

    def _retranslate_line_combo(self):
        # 按数据定位(弹层旋转后条目位置会变)
        for zh, data in self._line_opts:
            i = self.cb_line.findData(data)
            if i >= 0:
                self.cb_line.setItemText(i, tr(zh))

    def _retranslate_rx_enc_combo(self):
        for zh, data in self._rx_enc_opts:
            i = self.cb_rx_enc.findData(data)
            if i >= 0:
                self.cb_rx_enc.setItemText(i, tr(zh))

    def _retranslate_periodic_btn(self):
        self.btn_periodic.setText(
            tr("停止定时") if self._periodic_running else tr("开始定时"))

    def _build_left(self):
        left = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(left)
        lay.setContentsMargins(12, 10, 6, 10)
        lay.setSpacing(6)

        # -- 设备 --
        lay.addWidget(self._section("设备", "自动搜索附近设备，双击卡片可直接连接"))
        filt = QtWidgets.QHBoxLayout()
        filt.setSpacing(8)
        flab = QtWidgets.QLabel(tr("名称过滤"))
        flab.setObjectName("secHint")
        self._reg(lambda: flab.setText(tr("名称过滤")))
        filt.addWidget(flab)
        self.filter_edit = QtWidgets.QLineEdit()
        self.filter_edit.setPlaceholderText(tr("按名称或地址过滤…"))
        self._reg(lambda: self.filter_edit.setPlaceholderText(tr("按名称或地址过滤…")))
        self.filter_edit.textChanged.connect(self._on_filter)
        filt.addWidget(self.filter_edit)
        lay.addLayout(filt)

        self.dev_scroll = QtWidgets.QScrollArea()
        self.dev_scroll.setObjectName("devScroll")
        self.dev_scroll.setWidgetResizable(True)
        self.dev_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.dev_body = QtWidgets.QWidget()
        self.dev_lay = QtWidgets.QVBoxLayout(self.dev_body)
        self.dev_lay.setContentsMargins(0, 0, 4, 0)
        self.dev_lay.setSpacing(7)
        self.dev_hint = QtWidgets.QLabel(tr("尚未发现设备\n正在自动搜索附近的 BLE 设备…"))
        self._reg(lambda: self.dev_hint.setText(tr("尚未发现设备\n正在自动搜索附近的 BLE 设备…")))
        self.dev_hint.setAlignment(QtCore.Qt.AlignCenter)
        self.dev_hint.setObjectName("secHint")
        self.dev_hint.setWordWrap(True)
        self.dev_lay.addWidget(self.dev_hint)
        self.dev_lay.addStretch(1)
        self.dev_scroll.setWidget(self.dev_body)
        lay.addWidget(self.dev_scroll, 1)

        # -- 服务与特征 --
        lay.addWidget(self._section("服务与特征", "连接后自动识别读写特征"))
        self.svc_tree = QtWidgets.QTreeWidget()
        self.svc_tree.setHeaderLabels([tr("UUID"), tr("属性")])
        self._reg(lambda: self.svc_tree.setHeaderLabels([tr("UUID"), tr("属性")]))
        self.svc_tree.setColumnWidth(0, 250)
        self.svc_tree.setRootIsDecorated(True)
        lay.addWidget(self.svc_tree, 1)

        def combo_row(label_zh):
            row = QtWidgets.QHBoxLayout()
            row.setSpacing(8)
            lab = QtWidgets.QLabel(tr(label_zh))
            lab.setObjectName("secHint")
            lab.setMinimumWidth(32)
            self._reg(lambda: lab.setText(tr(label_zh)))
            row.addWidget(lab)
            cb = AnchoredCombo()
            cb.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            apply_popup_style(cb)
            row.addWidget(cb)
            return row, cb

        r1, self.cb_write = combo_row("写入")
        r2, self.cb_notify = combo_row("通知")
        self._chars_apply_timer = QtCore.QTimer(self)
        self._chars_apply_timer.setSingleShot(True)
        self._chars_apply_timer.setInterval(300)
        self._chars_apply_timer.timeout.connect(self._on_apply_chars)
        self.cb_write.currentIndexChanged.connect(self._on_chars_changed)
        self.cb_notify.currentIndexChanged.connect(self._on_chars_changed)
        lay.addLayout(r1)
        lay.addLayout(r2)
        self.btn_apply = QtWidgets.QPushButton(tr("应用特征设置"))
        self._reg(lambda: self.btn_apply.setText(tr("应用特征设置")))
        self.btn_apply.setEnabled(False)
        self.btn_apply.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_apply.clicked.connect(self._on_apply_chars)
        lay.addWidget(self.btn_apply)
        return left

    def _build_right(self):
        right = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(right)
        lay.setContentsMargins(6, 10, 12, 10)
        lay.setSpacing(8)

        # ---- 仪表屏(接收监视) ----
        screen = QtWidgets.QFrame()
        screen.setObjectName("screen")
        sly = QtWidgets.QVBoxLayout(screen)
        sly.setContentsMargins(1, 1, 1, 1)
        sly.setSpacing(0)

        top = QtWidgets.QFrame()
        top.setObjectName("screenStrip")
        tly = QtWidgets.QHBoxLayout(top)
        tly.setContentsMargins(12, 5, 12, 5)
        tly.setSpacing(12)
        slab = QtWidgets.QLabel(tr("接收监视"))
        slab.setObjectName("screenLabel")
        self._reg(lambda: slab.setText(tr("接收监视")))
        tly.addWidget(slab)
        self.seg_mode = Segmented((("ascii", "ASCII"), ("hex", "HEX"),
                                   ("mixed", tr("混合"))),
                                  value="ascii", dark=True)
        self._reg(lambda: self.seg_mode.set_option_text("mixed", tr("混合")))
        self.seg_mode.changed.connect(self._on_mode)
        tly.addWidget(self.seg_mode)
        tly.addStretch(1)
        self.chk_scroll = ToggleSwitch(tr("自动滚动"), self.tok, checked=True)
        self.chk_echo = ToggleSwitch(tr("回显发送"), self.tok, checked=True)
        self.chk_log = ToggleSwitch(tr("自动日志"), self.tok, checked=False)
        self._reg(lambda: self.chk_scroll.set_label(tr("自动滚动")))
        self._reg(lambda: self.chk_echo.set_label(tr("回显发送")))
        self._reg(lambda: self.chk_log.set_label(tr("自动日志")))
        self.chk_log.toggled.connect(self._toggle_auto_log)
        for c in (self.chk_scroll, self.chk_echo, self.chk_log):
            tly.addWidget(c)
        sly.addWidget(top)

        line1 = QtWidgets.QFrame()
        line1.setObjectName("screenLine")
        line1.setFixedHeight(1)
        sly.addWidget(line1)

        self.recv_text = QtWidgets.QTextEdit()
        self.recv_text.setObjectName("recvText")
        self.recv_text.setFont(mono_font(10))
        self.recv_text.setReadOnly(True)
        self.recv_text.setUndoRedoEnabled(False)
        self.recv_text.setAcceptRichText(True)
        self.recv_text.document().setMaximumBlockCount(0)
        sly.addWidget(self.recv_text, 1)
        self._show_recv_hint()

        line2 = QtWidgets.QFrame()
        line2.setObjectName("screenLine")
        line2.setFixedHeight(1)
        sly.addWidget(line2)

        bottom = QtWidgets.QFrame()
        bottom.setObjectName("screenStrip")
        bly = QtWidgets.QHBoxLayout(bottom)
        bly.setContentsMargins(12, 5, 12, 5)
        bly.setSpacing(8)

        def ro(label, var_holder):
            lab = QtWidgets.QLabel(label)
            lab.setObjectName("roLabel")
            val = QtWidgets.QLabel(var_holder)
            val.setObjectName("roValue")
            val.setFont(mono_font(9))
            bly.addWidget(lab)
            bly.addWidget(val)
            return val

        self.ro_rx = ro("RX", tr("%d 字节 / %d 包") % (0, 0))
        bly.addSpacing(12)
        self.ro_tx = ro("TX", tr("%d 字节") % 0)
        bly.addStretch(1)
        b1 = QtWidgets.QPushButton(tr("保存日志..."))
        b1.setObjectName("dbtn")
        self._reg(lambda: b1.setText(tr("保存日志...")))
        b1.setCursor(QtCore.Qt.PointingHandCursor)
        b1.clicked.connect(self._on_save_log)
        b2 = QtWidgets.QPushButton(tr("清空"))
        b2.setObjectName("dbtn")
        self._reg(lambda: b2.setText(tr("清空")))
        b2.setCursor(QtCore.Qt.PointingHandCursor)
        b2.clicked.connect(self._on_clear)
        bly.addWidget(b1)
        bly.addWidget(b2)
        sly.addWidget(bottom)
        lay.addWidget(screen, 1)

        # ---- 发送 ----
        lay.addWidget(self._section("发送", "HEX 字节可用空格分隔"))
        txrow = QtWidgets.QHBoxLayout()
        txrow.setSpacing(10)
        self.send_text = QtWidgets.QTextEdit()
        self.send_text.setObjectName("sendText")
        self.send_text.setFont(mono_font(10))
        self.send_text.setAcceptRichText(False)
        self.send_text.setFixedHeight(84)
        self.send_text.setTabChangesFocus(True)
        txrow.addWidget(self.send_text, 1)
        self.btn_send = QtWidgets.QPushButton(tr("发 送"))
        self.btn_send.setObjectName("sendBtn")
        self._reg(lambda: self.btn_send.setText(tr("发 送")))
        self.btn_send.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_send.setEnabled(False)
        self.btn_send.clicked.connect(self._on_send)
        txrow.addWidget(self.btn_send)
        lay.addLayout(txrow)

        opt1 = QtWidgets.QHBoxLayout()
        opt1.setSpacing(8)
        lab = QtWidgets.QLabel(tr("格式"))
        lab.setObjectName("secHint")
        self._reg(lambda l=lab: l.setText(tr("格式")))
        opt1.addWidget(lab)
        self.seg_fmt = Segmented((("ascii", "ASCII"), ("hex", "HEX")), value="ascii")
        opt1.addWidget(self.seg_fmt)
        lab = QtWidgets.QLabel(tr("编码"))
        lab.setObjectName("secHint")
        self._reg(lambda l=lab: l.setText(tr("编码")))
        opt1.addWidget(lab)
        self.cb_encoding = AnchoredCombo()
        self.cb_encoding.addItems(["utf-8", "gbk"])
        apply_popup_style(self.cb_encoding)
        opt1.addWidget(self.cb_encoding)
        lab = QtWidgets.QLabel(tr("行尾"))
        lab.setObjectName("secHint")
        self._reg(lambda l=lab: l.setText(tr("行尾")))
        opt1.addWidget(lab)
        self.cb_line = AnchoredCombo()
        # (显示词条, 真实行尾字节): 显示随语言变, 数据不变
        self._line_opts = [("无", ""), ("\\r", "\r"), ("\\n", "\n"), ("\\r\\n", "\r\n")]
        for zh, data in self._line_opts:
            self.cb_line.addItem(tr(zh), data)
        self._reg(self._retranslate_line_combo)
        apply_popup_style(self.cb_line)
        opt1.addWidget(self.cb_line)
        lab = QtWidgets.QLabel(tr("解码"))
        lab.setObjectName("secHint")
        self._reg(lambda l=lab: l.setText(tr("解码")))
        opt1.addWidget(lab)
        self.cb_rx_enc = AnchoredCombo()
        # (显示词条, 解码方式): 显示随语言变, 数据不变
        self._rx_enc_opts = [("UTF-8", "utf-8"), ("GBK", "gbk"), ("转义", "escape")]
        for zh, data in self._rx_enc_opts:
            self.cb_rx_enc.addItem(tr(zh), data)
        self._reg(self._retranslate_rx_enc_combo)
        self.cb_rx_enc.currentIndexChanged.connect(lambda _: self._flush_rx_frame())
        apply_popup_style(self.cb_rx_enc)
        opt1.addWidget(self.cb_rx_enc)
        lab = QtWidgets.QLabel(tr("超时时间"))
        lab.setObjectName("secHint")
        self._reg(lambda l=lab: l.setText(tr("超时时间")))
        opt1.addWidget(lab)
        self.edit_coalesce = QtWidgets.QLineEdit("150")
        self.edit_coalesce.setFixedWidth(56)
        self.edit_coalesce.setToolTip(tr("同一帧被拆成多包时, 静默此时间后合并为一行显示; 0=每包一行"))
        self._reg(lambda: self.edit_coalesce.setToolTip(
            tr("同一帧被拆成多包时, 静默此时间后合并为一行显示; 0=每包一行")))
        self.edit_coalesce.textChanged.connect(self._on_coalesce_changed)
        opt1.addWidget(self.edit_coalesce)
        mslab = QtWidgets.QLabel("ms")
        mslab.setObjectName("secHint")
        opt1.addWidget(mslab)
        opt1.addStretch(1)
        lay.addLayout(opt1)

        opt2 = QtWidgets.QHBoxLayout()
        opt2.setSpacing(8)
        lab = QtWidgets.QLabel(tr("定时发送(ms)"))
        lab.setObjectName("secHint")
        self._reg(lambda: lab.setText(tr("定时发送(ms)")))
        opt2.addWidget(lab)
        self.periodic_edit = QtWidgets.QLineEdit("1000")
        self.periodic_edit.setFixedWidth(76)
        opt2.addWidget(self.periodic_edit)
        self.btn_periodic = QtWidgets.QPushButton(tr("开始定时"))
        self._reg(self._retranslate_periodic_btn)
        self.btn_periodic.setEnabled(False)
        self.btn_periodic.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_periodic.clicked.connect(self._on_periodic)
        opt2.addWidget(self.btn_periodic)
        hint = QtWidgets.QLabel(tr("使用当前输入框内容, 可随时修改"))
        hint.setObjectName("secHint")
        self._reg(lambda: hint.setText(tr("使用当前输入框内容, 可随时修改")))
        opt2.addWidget(hint)
        opt2.addStretch(1)
        lay.addLayout(opt2)

        # ---- 预设命令 ----
        lay.addWidget(self._section("预设命令", "点「发」按当前格式快速发送"))
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(6)
        self.multi_edits = []
        for i in range(8):
            r, c = divmod(i, 2)
            edit = QtWidgets.QLineEdit()
            btn = QtWidgets.QPushButton(tr("发", "mini"))
            btn.setObjectName("miniBtn")
            self._reg(lambda b=btn: b.setText(tr("发", "mini")))
            btn.setFixedWidth(40)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, idx=i: self._on_send_multi(idx))
            cellw = QtWidgets.QHBoxLayout()
            cellw.setSpacing(6)
            cellw.addWidget(edit, 1)
            cellw.addWidget(btn)
            grid.addLayout(cellw, r, c)
            self.multi_edits.append(edit)
        lay.addLayout(grid)
        return right

    def _section(self, title, hint=None):
        w = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(3)
        row = QtWidgets.QHBoxLayout()
        t = QtWidgets.QLabel(tr(title))
        t.setObjectName("secTitle")
        self._reg(lambda: t.setText(tr(title)))
        row.addWidget(t)
        if hint:
            h = QtWidgets.QLabel(tr(hint))
            h.setObjectName("secHint")
            self._reg(lambda: h.setText(tr(hint)))
            row.addStretch(1)
            row.addWidget(h)
        v.addLayout(row)
        line = QtWidgets.QFrame()
        line.setObjectName("secLine")
        line.setFixedHeight(1)
        v.addWidget(line)
        return w

    def _build_menu(self):
        mb = self.menuBar()
        m_file = mb.addMenu(tr("文件"))
        self._reg(lambda: m_file.setTitle(tr("文件")))
        act = m_file.addAction(tr("清空接收区"), self._on_clear)
        self._reg(lambda a=act: a.setText(tr("清空接收区")))
        act = m_file.addAction(tr("保存日志..."), self._on_save_log)
        self._reg(lambda a=act: a.setText(tr("保存日志...")))
        m_file.addSeparator()
        act = m_file.addAction(tr("退出"), self.close)
        self._reg(lambda a=act: a.setText(tr("退出")))
        m_tools = mb.addMenu(tr("工具"))
        self._reg(lambda: m_tools.setTitle(tr("工具")))
        self._act_light = m_tools.addAction(tr("浅色模式"))
        self._reg(lambda: self._act_light.setText(tr("浅色模式")))
        self._act_light.setCheckable(True)
        self._act_light.triggered.connect(lambda: self._set_theme("light"))
        self._act_dark = m_tools.addAction(tr("深色模式"))
        self._reg(lambda: self._act_dark.setText(tr("深色模式")))
        self._act_dark.setCheckable(True)
        self._act_dark.triggered.connect(lambda: self._set_theme("dark"))
        self._act_light.setChecked(self.theme_name == "light")
        self._act_dark.setChecked(self.theme_name == "dark")
        m_tools.addSeparator()
        m_lang = m_tools.addMenu(tr("语言"))
        self._reg(lambda: m_lang.setTitle(tr("语言")))
        self._act_zh = m_lang.addAction("中文")
        self._act_zh.setCheckable(True)
        self._act_zh.triggered.connect(lambda: self._set_language("zh"))
        self._act_en = m_lang.addAction("English")
        self._act_en.setCheckable(True)
        self._act_en.triggered.connect(lambda: self._set_language("en"))
        self._act_zh.setChecked(self.lang_name == "zh")
        self._act_en.setChecked(self.lang_name == "en")
        m_help = mb.addMenu(tr("帮助"))
        self._reg(lambda: m_help.setTitle(tr("帮助")))
        act = m_help.addAction(tr("使用说明"), self._show_help)
        self._reg(lambda a=act: a.setText(tr("使用说明")))
        act = m_help.addAction(tr("关于"), self._show_about)
        self._reg(lambda a=act: a.setText(tr("关于")))

    # ================= 主题 =================
    def _set_theme(self, name):
        if name not in THEMES or name == self.theme_name:
            return
        self.theme_name = name
        self.tok = THEMES[name]
        self._apply_theme_colors()
        self._act_light.setChecked(name == "light")
        self._act_dark.setChecked(name == "dark")
        self._set_dark_titlebar(name == "dark")
        self._save_config()

    def _apply_theme_colors(self):
        app = QtWidgets.QApplication.instance()
        app.setStyleSheet(build_qss(self.tok))
        for card in self.cards.values():
            card.set_theme(self.tok)
        for tw in (getattr(self, "chk_scroll", None),
                   getattr(self, "chk_echo", None),
                   getattr(self, "chk_log", None)):
            if tw is not None:
                tw.set_theme(self.tok)
        # 拖选高亮色: 除 QSS 外再写调色板, 保证选中可见
        pal = self.pill_dev.palette()
        pal.setColor(QtGui.QPalette.Highlight, QtGui.QColor(self.tok["ACCENT"]))
        pal.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor(self.tok["SEL_FG"]))
        self.pill_dev.setPalette(pal)
        self._paint_pill_dot()
        self._update_status()

    def _set_dark_titlebar(self, dark):
        """Win10/11 深色标题栏, 与深色主题成套。"""
        try:
            import ctypes
            hwnd = int(self.winId())
            val = ctypes.c_int(1 if dark else 0)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(val), ctypes.sizeof(val))
        except Exception:
            pass

    def _paint_pill_dot(self):
        color = self.tok["IDLE_GRAY"]
        if self.conn_state == "connected":
            color = self.tok["OK_GREEN"]
        elif self.conn_state == "connecting":
            color = self.tok["WARN_AMBER"]
        pm = QtGui.QPixmap(11, 11)
        pm.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(pm)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(color))
        p.drawEllipse(1, 1, 9, 9)
        p.end()
        self.pill_dot.setPixmap(pm)

    # ================= 引擎事件 =================
    def _on_event(self, ev):
        t = ev.get("type")
        if t == "device_found":
            self._pending_devices[ev["address"]] = {"name": ev["name"],
                                                    "rssi": ev.get("rssi"),
                                                    "seen": time.time()}
        elif t == "services":
            self._on_services(ev["services"])
        elif t == "uart_ready":
            self._on_uart_ready(ev)
        elif t == "rx":
            self._on_rx(ev["data"], ev.get("ts"))
        elif t == "tx":
            self._on_tx(ev["data"], ev.get("ts"))
        elif t == "log":
            self._append_line(ev["text"], ev.get("tag", "info"))
        elif t == "error":
            self._append_line(tr("[错误] %s") % ev["text"], "error")
        elif t == "conn_state":
            self._on_conn_state(ev["state"])
        elif t == "scan_state":
            self._on_scan_state(ev["state"])
        elif t == "periodic_started":
            self._periodic_running = True
            self._retranslate_periodic_btn()
        elif t == "periodic_stopped":
            self._periodic_running = False
            self._retranslate_periodic_btn()

    # ---------------- 设备列表 ----------------
    def _flush_devices(self):
        self._expire_devices()
        if not self._pending_devices:
            return
        pending, self._pending_devices = self._pending_devices, {}
        key = self.filter_edit.text().strip().lower()
        for addr, info in pending.items():
            self.devices[addr] = info
            visible = (not key or key in info["name"].lower() or key in addr.lower())
            card = self.cards.get(addr)
            if card is None:
                card = DeviceCard(addr, info["name"], info["rssi"], self.tok)
                card.connect_clicked.connect(self._on_connect)
                card.selected.connect(self._select_device)
                card.double_clicked.connect(self._on_connect)
                card.conn_btn.setEnabled(self.conn_state == "idle")
                self.cards[addr] = card
                self.dev_lay.insertWidget(self.dev_lay.count() - 1, card)
            else:
                card.name_lbl.setText(info["name"])
                card.set_rssi(info["rssi"])
            card.setVisible(visible)
        self._update_dev_hint()

    def _expire_devices(self):
        """断电/走远的设备停播后从列表移除, 连接中的设备保留。"""
        now = time.time()
        gone = []
        for addr, info in self.devices.items():
            if addr == self._conn_addr:
                continue
            if now - info.get("seen", now) > DEV_STALE_SEC:
                gone.append(addr)
        for addr in gone:
            self.devices.pop(addr, None)
            card = self.cards.pop(addr, None)
            if card is not None:
                self.dev_lay.removeWidget(card)
                card.setParent(None)
                card.deleteLater()
            if self.selected_addr == addr:
                self.selected_addr = None
        if gone:
            self._update_dev_hint()
            self._update_status()

    def _on_filter(self):
        key = self.filter_edit.text().strip().lower()
        for addr, card in self.cards.items():
            info = self.devices.get(addr, {"name": "", "rssi": None})
            visible = (not key or key in info["name"].lower() or key in addr.lower())
            card.setVisible(visible)
        self._update_dev_hint()

    def _update_dev_hint(self):
        any_visible = any(c.isVisible() for c in self.cards.values())
        self.dev_hint.setVisible(not any_visible)

    def _select_device(self, addr):
        self.selected_addr = addr
        for a, card in self.cards.items():
            card.set_selected(a == addr)
        self._update_status()

    def _start_scan(self):
        if self._shutting_down or self.engine._scan_active:
            return
        self.engine.start_scan(None)

    def _on_scan_state(self, state):
        self.scanning = state == "scanning"
        if state == "stopped" and not self._shutting_down:
            QtCore.QTimer.singleShot(3000, self._start_scan)

    # ---------------- 连接 / 特征 ----------------
    def _on_connect(self, addr):
        if self.conn_state != "idle":
            return
        info = self.devices.get(addr, {"name": addr, "rssi": None})
        self._append_line(tr("[操作] 正在连接 %s (%s) ...") % (info["name"], addr), "info")
        self._conn_addr = addr
        self._select_device(addr)
        self.engine.connect(addr)

    def _on_disconnect(self):
        self.engine.disconnect()

    def _on_conn_state(self, state):
        self._flush_rx_frame()   # 断开/切状态时不再留半帧在缓冲里
        self.conn_state = state
        connected = state == "connected"
        self.btn_disconnect.setEnabled(state in ("connected", "connecting"))
        self.btn_send.setEnabled(connected)
        self.btn_periodic.setEnabled(connected)
        for card in self.cards.values():
            card.conn_btn.setEnabled(state == "idle")
        if state == "idle":
            # 断开/连接失败一律清理特征区与重放缓存
            self.svc_tree.clear()
            self.cb_write.clear()
            self.cb_notify.clear()
            self.btn_apply.setEnabled(False)
            self.char_options = []
            self._last_services = None
            self._last_uart_ev = None
            self._conn_addr = None
        self._update_status()
        self._update_recv_hint()

    def _on_services(self, services):
        self._last_services = services
        self.svc_tree.clear()
        self.char_options = []
        for svc in services:
            top = QtWidgets.QTreeWidgetItem([self._uuid_label(svc["uuid"]), tr("服务")])
            self.svc_tree.addTopLevelItem(top)
            top.setExpanded(True)
            for c in svc["characteristics"]:
                props = ",".join(c["props"])
                top.addChild(QtWidgets.QTreeWidgetItem(
                    [self._uuid_label(c["uuid"]), props]))
                disp = "%s  [%s]" % (self._uuid_label(c["uuid"]), props)
                self.char_options.append((disp, (c["uuid"] or "").lower()))
        self.cb_write.blockSignals(True)
        self.cb_notify.blockSignals(True)
        self.cb_write.clear()
        self.cb_notify.clear()
        for disp, uuid in self.char_options:
            self.cb_write.addItem(disp, uuid)
            self.cb_notify.addItem(disp, uuid)
        self.cb_write.blockSignals(False)
        self.cb_notify.blockSignals(False)
        self.btn_apply.setEnabled(bool(self.char_options))
        if self._last_uart_ev is not None:
            self._on_uart_ready(self._last_uart_ev)

    def _on_uart_ready(self, ev):
        self._last_uart_ev = ev
        write_uuid = (ev.get("write") or "").lower()
        notify_uuid = (ev.get("notify") or "").lower()
        # 该设备上次手动指定过的特征优先于自动识别, 免得每次重连重选
        prefs = self._char_prefs.get(self._conn_addr or "") or {}
        pw = (prefs.get("write") or "").lower()
        pn = (prefs.get("notify") or "").lower()
        use_prefs = (pw and pn
                     and self.cb_write.findData(pw) >= 0
                     and self.cb_notify.findData(pn) >= 0
                     and (pw, pn) != (write_uuid, notify_uuid))
        if use_prefs:
            write_uuid, notify_uuid = pw, pn
        wi = self.cb_write.findData(write_uuid)
        ni = self.cb_notify.findData(notify_uuid)
        # 兜底: UUID 对不上时按常见形态配对补齐, 保证两个框不留空
        if wi < 0 and ni >= 0:
            wi = ni
        if ni < 0 and wi >= 0:
            ni = wi
        if wi < 0 and self.char_options:
            wi = ni = 0
        self.cb_write.blockSignals(True)
        self.cb_notify.blockSignals(True)
        try:
            if wi >= 0:
                self.cb_write.setCurrentIndex(wi)
            if ni >= 0:
                self.cb_notify.setCurrentIndex(ni)
        finally:
            self.cb_write.blockSignals(False)
            self.cb_notify.blockSignals(False)
        if use_prefs:
            # 引擎按自动识别订阅的是另一组特征, 切到记忆的组合并重订通知
            self.engine.apply_chars(pw, pn)

    def _on_apply_chars(self):
        if self.conn_state != "connected":
            return
        wi, ni = self.cb_write.currentIndex(), self.cb_notify.currentIndex()
        if wi < 0 or ni < 0:
            QtWidgets.QMessageBox.information(
                self, tr("提示"), tr("请先选择写入特征和通知特征"))
            return
        w_uuid = self.cb_write.itemData(wi)
        n_uuid = self.cb_notify.itemData(ni)
        self.engine.apply_chars(w_uuid, n_uuid)
        if self._conn_addr:
            self._char_prefs[self._conn_addr] = {"write": w_uuid, "notify": n_uuid}
            self._save_config()

    def _on_chars_changed(self, _idx):
        # 下拉一改就生效(防抖 300ms), 不必再点「应用特征设置」
        if self.conn_state == "connected" and self.char_options:
            self._chars_apply_timer.start()

    @staticmethod
    def _uuid_label(uuid):
        u = (uuid or "").lower()
        return tr(KNOWN_UUIDS.get(u, u))

    # ---------------- 收发显示 ----------------
    def _coalesce_ms(self):
        """超时时间(拼包静默间隙)毫秒数; 空/乱输入按 0(不拼包)处理"""
        try:
            v = int((self.edit_coalesce.text() or "").strip())
        except ValueError:
            return 0
        return max(0, min(2000, v))

    def _on_rx(self, data, ts=None):
        self.rx_bytes += len(data)
        self.rx_packets += 1
        self._status_dirty = True
        gap = self._coalesce_ms()
        if gap <= 0:
            self._append_rx(data, ts)
            return
        if not self._rx_buf:
            self._rx_buf_ts = ts if ts is not None else time.time()
        self._rx_buf += data
        now = ts if ts is not None else time.time()
        # 静默窗口在每包后重开; 上限避免持续细流一直扣着不显示
        if (len(self._rx_buf) >= RX_COALESCE_MAX_BYTES
                or now - self._rx_buf_ts > RX_COALESCE_MAX_HOLD):
            self._flush_rx_frame()
        else:
            self._t_rx_flush.start(gap)

    def _append_rx(self, data, ts):
        text = format_bytes(data, self._mode(), self._rx_encoding())
        self._append_line("[%s] RX: %s" % (self._ts(ts), text), "rx")

    def _flush_rx_frame(self):
        """把拼包缓冲合并为一行显示(静默间隙到点/切换模式/断开/退出时调用)"""
        self._t_rx_flush.stop()
        if not self._rx_buf:
            return
        data, ts = bytes(self._rx_buf), self._rx_buf_ts
        self._rx_buf.clear()
        self._rx_buf_ts = None
        self._append_rx(data, ts)

    def _on_coalesce_changed(self, _text=None):
        if self._coalesce_ms() <= 0:
            self._flush_rx_frame()   # 关拼包时把已缓冲的帧放出来

    def _on_tx(self, data, ts=None):
        self.tx_bytes += len(data)
        if self.chk_echo.isChecked():
            # 回显按发送编码解(与生成字节时一致), 避免发 GBK 时回显成转义
            text = format_bytes(data, self._mode(),
                                self.cb_encoding.currentText() or "utf-8")
            self._append_line("[%s] TX: %s" % (self._ts(ts), text), "tx")
        self._status_dirty = True

    def _mode(self):
        return self.seg_mode.value() or "ascii"

    def _rx_encoding(self):
        return self.cb_rx_enc.currentData() or "utf-8"

    def _append_line(self, line, tag):
        self.receive_lines.append(line)
        self.recv_tags.append(tag)
        self._write_auto_log(line)
        self._pending_lines.append((line, tag))

    def _flush_lines(self):
        if self._pending_lines:
            if self._recv_hint_visible:
                self.recv_text.clear()
                self._recv_hint_visible = False
            items, self._pending_lines = self._pending_lines, []
            cur = self.recv_text.textCursor()
            cur.movePosition(QtGui.QTextCursor.End)
            colors = {"rx": self.tok["SCREEN_FG"], "tx": self.tok["SCREEN_TX"],
                      "info": self.tok["SCREEN_DIM"], "warn": self.tok["SCREEN_WARN"],
                      "error": self.tok["SCREEN_ERR"]}
            parts = []
            for line, tag in items:
                parts.append('<span style="color:%s">%s</span>'
                             % (colors.get(tag, self.tok["SCREEN_FG"]),
                                html.escape(line).replace(" ", "&nbsp;")))
            cur.insertHtml("<br>".join(parts) + "<br>")
            self._trim_recv()
            if self.chk_scroll.isChecked():
                sb = self.recv_text.verticalScrollBar()
                sb.setValue(sb.maximum())
            self._update_recv_hint()
        if self._status_dirty:
            self._status_dirty = False
            self._update_status()

    def _trim_recv(self):
        doc = self.recv_text.document()
        extra = doc.blockCount() - RECV_MAX_LINES
        if extra > 0:
            cur = QtGui.QTextCursor(doc)
            cur.movePosition(QtGui.QTextCursor.Down, QtGui.QTextCursor.KeepAnchor,
                             extra + (RECV_MAX_LINES - RECV_TRIM_TO))
            cur.removeSelectedText()

    def _update_recv_hint(self):
        if self.receive_lines:
            return
        if self.conn_state == "connected":
            msg = tr("已连接，等待收发数据…<br>MCU 的回复将实时显示在这里")
        else:
            msg = tr("请在左侧选择设备并点击「连接」<br>连接后即可在此实时查看收发数据")
        self.recv_text.setHtml(
            '<div style="color:%s; text-align:center; font-size:10.5pt;'
            ' margin-top:80px;">%s</div>' % (self.tok["SCREEN_DIM"], msg))
        self._recv_hint_visible = True

    def _show_recv_hint(self):
        self._update_recv_hint()

    def _on_clear(self):
        self._t_rx_flush.stop()
        self._rx_buf.clear()
        self._rx_buf_ts = None
        self.recv_text.clear()
        self.receive_lines.clear()
        self.recv_tags.clear()
        self._pending_lines.clear()
        self.rx_bytes = self.tx_bytes = self.rx_packets = 0
        self._status_dirty = True
        self._flush_lines()
        self._update_recv_hint()

    def _on_mode(self, _key):
        self._flush_rx_frame()   # 切换显示模式时把缓冲中的帧放出来

    def _on_send(self):
        if self.conn_state != "connected":
            return
        try:
            data = self._build_data_from(self.send_text.toPlainText().rstrip("\n"))
        except ValueError as e:
            QtWidgets.QMessageBox.critical(self, tr("发送格式错误"), str(e))
            return
        if data:
            self.engine.send(data)

    def _on_send_multi(self, idx):
        if self.conn_state != "connected":
            return
        content = self.multi_edits[idx].text().strip()
        if not content:
            return
        try:
            data = self._build_data_from(content)
        except ValueError as e:
            QtWidgets.QMessageBox.critical(self, tr("发送格式错误"),
                                           tr("第 %d 条: %s") % (idx + 1, e))
            return
        if data:
            self.engine.send(data)

    def _current_cfg(self):
        return {
            "cmd": self.send_text.toPlainText().rstrip("\n"),
            "fmt": self.seg_fmt.value() or "ascii",
            "encoding": self.cb_encoding.currentText(),
            "line": self.cb_line.currentData() or "",
        }

    def _build_data_from(self, cmd):
        cfg = self._current_cfg()
        cfg["cmd"] = cmd
        return build_data(cfg)

    def _periodic_snapshot(self):
        cfg = self._current_cfg()
        self.engine.periodic_cfg.update(
            cmd=cfg["cmd"], fmt=cfg["fmt"],
            encoding=cfg["encoding"], line=cfg["line"])

    def _on_periodic(self):
        if self.conn_state != "connected":
            return
        if not self._periodic_running:
            try:
                ms = int(self.periodic_edit.text())
                if ms < 50:
                    raise ValueError
            except ValueError:
                QtWidgets.QMessageBox.critical(
                    self, tr("错误"), tr("定时周期需为不小于 50 的整数(毫秒)"))
                return
            self.engine.start_periodic(ms / 1000.0)
        else:
            self.engine.stop_periodic()

    # ---------------- 状态读数 ----------------
    def _update_status(self):
        # 连接中/已连接只显示"实际连接的设备", 列表选中不再污染它(易误读)
        if self.conn_state in ("connected", "connecting"):
            addr = self._conn_addr
        else:
            addr = self.selected_addr
        dev = "-"
        if addr and addr in self.devices:
            dev = "%s (%s)" % (self.devices[addr]["name"], addr)
        elif addr:
            dev = addr
        mtu = "-"
        if self.conn_state == "connected":
            mtu = str(getattr(self.engine.client, "mtu_size", 23))
        state_txt = {"idle": tr("空闲"), "scanning": tr("扫描中..."),
                     "connecting": tr("连接中..."), "connected": tr("已连接")}.get(
                         self.conn_state, self.conn_state)
        self.g_mtu.setText(mtu)
        self.g_rx.setText(tr("%d 字节 / %d 包") % (self.rx_bytes, self.rx_packets))
        self.g_tx.setText(tr("%d 字节") % self.tx_bytes)
        self.ro_rx.setText(tr("%d 字节 / %d 包") % (self.rx_bytes, self.rx_packets))
        self.ro_tx.setText(tr("%d 字节") % self.tx_bytes)
        dev_txt = dev if dev != "-" else tr("未选择设备")
        # 文本未变就不重设 setText, 否则收发频繁时会清掉用户正在做的拖选
        if self.pill_state.text() != state_txt:
            self.pill_state.setText(state_txt)
        if self.pill_dev.text() != dev_txt:
            self.pill_dev.setText(dev_txt)
        self._paint_pill_dot()

    # ---------------- 自动日志 ----------------
    def _toggle_auto_log(self, on):
        if on:
            self._open_auto_log()
        else:
            self._close_auto_log()

    def _open_auto_log(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        path = os.path.join(LOG_DIR, time.strftime("ble_%Y%m%d.log"))
        self.auto_log_path = path
        if self.auto_log_fp is not None:
            self.auto_log_fp.close()
        self.auto_log_fp = open(path, "a", encoding="utf-8")
        self.auto_log_fp.write(tr("===== %s 会话开始 =====")
                               % time.strftime("%Y-%m-%d %H:%M:%S") + "\n")

    def _close_auto_log(self):
        if self.auto_log_fp is not None:
            try:
                self.auto_log_fp.flush()
                self.auto_log_fp.write(tr("===== %s 会话结束 =====")
                                       % time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                self.auto_log_fp.close()
            except Exception:
                pass
        self.auto_log_fp = None

    def _write_auto_log(self, line):
        if self.auto_log_fp is None:
            return
        if self.auto_log_path and time.strftime("ble_%Y%m%d.log") != os.path.basename(self.auto_log_path):
            self._open_auto_log()
        try:
            self.auto_log_fp.write(line + "\n")
        except Exception:
            pass

    def _flush_log(self):
        if self.auto_log_fp is not None:
            try:
                self.auto_log_fp.flush()
            except Exception:
                pass

    def _on_save_log(self):
        if not self.receive_lines:
            QtWidgets.QMessageBox.information(
                self, tr("提示"), tr("接收区没有可保存的内容"))
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, tr("保存日志"), time.strftime("ble_log_%Y%m%d_%H%M%S.txt"),
            tr("文本文件 (*.txt);;所有文件 (*)"))
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write((tr("===== 坤坤蓝牙助手日志 %s =====")
                         % time.strftime("%Y-%m-%d %H:%M:%S")) + "\n")
                f.write("\n".join(self.receive_lines) + "\n")
            QtWidgets.QMessageBox.information(
                self, tr("完成"), tr("日志已保存到:\n%s") % path)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, tr("保存失败"), str(e))

    def _ts(self, t=None):
        if t is None:
            t = time.time()
        return time.strftime("%H:%M:%S", time.localtime(t)) + (".%03d" % (int(t * 1000) % 1000))

    # ---------------- 帮助 / 关于 ----------------
    def _show_help(self):
        QtWidgets.QMessageBox.information(
            self, tr("使用说明"),
            tr("1. 给蓝牙模块上电, 打开程序(自动持续扫描)\n"
               "2. 在左侧列表选中你的模块(可按名称过滤), 双击卡片连接\n"
               "3. 连接后自动识别读写特征(支持 HC-04/HM-10、NUS、ISSC 及自定义)\n"
               "4. 在输入框填写命令, 选择格式(ASCII/HEX)和行尾, 点【发送】\n"
               "5. MCU 的回复会实时显示在监视屏\n\n"
               "提示:\n"
               " - BLE 链路没有波特率概念, 波特率只在模块<->MCU 串口间有效\n"
               " - 定时发送可做周期轮询; 预设命令可快速重复发送\n"
               " - 菜单【工具】可切换浅色/深色主题\n"
               " - 详细说明见同目录 使用说明.md"))

    def _show_about(self):
        QtWidgets.QMessageBox.about(
            self, tr("关于"),
            tr("%s V%s\n\n电脑BLE ↔ 模块 ↔ MCU 无线串口调试工具\n"
               "自动识别 HC-04/HM-10/NUS 等常见透传服务\n"
               "界面: PySide6(Qt)   通信: bleak") % (APP_NAME, APP_VERSION))

    # ---------------- 配置持久化 ----------------
    def _peek_config(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _load_config(self, cfg):
        try:
            self._char_prefs = {}
            for addr, p in (cfg.get("char_prefs") or {}).items():
                if isinstance(p, dict):
                    self._char_prefs[addr] = {
                        "write": (p.get("write") or "").lower(),
                        "notify": (p.get("notify") or "").lower()}
            self.chk_echo.setChecked(bool(cfg.get("echo_tx", True)))
            self.chk_scroll.setChecked(bool(cfg.get("auto_scroll", True)))
            self.seg_fmt.set_value(cfg.get("send_fmt", "ascii"))
            self.seg_mode.set_value(cfg.get("rx_mode", "ascii"))
            idx = self.cb_rx_enc.findData(cfg.get("rx_encoding", "utf-8"))
            if idx >= 0:
                self.cb_rx_enc.blockSignals(True)   # 载入期勿触发拼包冲刷(定时器未建)
                self.cb_rx_enc.setCurrentIndex(idx)
                self.cb_rx_enc.blockSignals(False)
            try:
                ms = int(cfg.get("rx_coalesce_ms", 150))
            except (TypeError, ValueError):
                ms = 150
            self.edit_coalesce.blockSignals(True)
            self.edit_coalesce.setText(str(max(0, min(2000, ms))))
            self.edit_coalesce.blockSignals(False)
            idx = self.cb_encoding.findText(cfg.get("send_encoding", "utf-8"))
            if idx >= 0:
                self.cb_encoding.setCurrentIndex(idx)
            # 行尾: 新版存真实后缀字节, 兼容旧版存的显示文本("无"/"\\r"/...)
            legacy_line = {"无": "", "\\r": "\r", "\\n": "\n", "\\r\\n": "\r\n"}
            line_tok = cfg.get("line_ending", "")
            line_tok = legacy_line.get(line_tok, line_tok)
            idx = self.cb_line.findData(line_tok)
            if idx >= 0:
                self.cb_line.setCurrentIndex(idx)
            self.periodic_edit.setText(str(cfg.get("periodic_ms", 1000)))
            self.send_text.setPlainText(cfg.get("send_content", ""))
            ms = cfg.get("multi_strings") or []
            for i, edit in enumerate(self.multi_edits):
                if i < len(ms):
                    edit.setText(ms[i] or "")
            geo = cfg.get("geometry_qt")
            if geo:
                try:
                    self.restoreGeometry(bytes.fromhex(geo))
                except Exception:
                    pass
            if cfg.get("maximized"):
                self.showMaximized()
            if cfg.get("auto_log"):
                self.chk_log.setChecked(True)   # toggled 信号会打开日志
        except Exception:
            pass

    def _save_config(self):
        cfg = {
            "theme": self.theme_name,
            "lang": self.lang_name,
            "char_prefs": self._char_prefs,
            "rx_mode": self.seg_mode.value() or "ascii",
            "rx_encoding": self.cb_rx_enc.currentData() or "utf-8",
            "rx_coalesce_ms": self._coalesce_ms(),
            "echo_tx": self.chk_echo.isChecked(),
            "auto_scroll": self.chk_scroll.isChecked(),
            "send_fmt": self.seg_fmt.value() or "ascii",
            "send_encoding": self.cb_encoding.currentText(),
            "line_ending": self.cb_line.currentData() or "",
            "periodic_ms": self.periodic_edit.text(),
            "send_content": self.send_text.toPlainText().rstrip("\n"),
            "multi_strings": [e.text() for e in self.multi_edits],
            "geometry_qt": bytes(self.saveGeometry()).hex(),
            "maximized": self.isMaximized(),
            "auto_log": self.chk_log.isChecked(),
        }
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ---------------- 退出 ----------------
    def closeEvent(self, ev):
        self._shutting_down = True
        self._flush_rx_frame()
        self._save_config()
        self._close_auto_log()
        self.engine.shutdown()
        super().closeEvent(ev)


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(ui_font(10))
    app.setWindowIcon(QtGui.QIcon(resource_path("app_icon.png")))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
