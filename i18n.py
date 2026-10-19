# -*- coding: utf-8 -*-
"""界面文案双语(中文/英文)。

以中文原文为键(gettext 风格), 缺词条时回退原文; 同一中文在不同语境
含义不同时用 ctx 区分, 键为 "ctx|原文"。语言由 set_lang() 全局切换,
UI 与 ble_engine 的运行日志都走 tr()。
"""

LANG = "zh"


def tr(s, ctx=""):
    if LANG != "en":
        return s
    key = (ctx + "|" + s) if ctx else s
    return EN.get(key, EN.get(s, s))


def set_lang(name):
    global LANG
    LANG = "en" if name == "en" else "zh"


def get_lang():
    return LANG


EN = {
    # ---- 菜单 ----
    "文件": "File",
    "清空接收区": "Clear Receive Area",
    "保存日志...": "Save Log...",
    "退出": "Exit",
    "工具": "Tools",
    "浅色模式": "Light Mode",
    "深色模式": "Dark Mode",
    "语言": "Language",
    "帮助": "Help",
    "使用说明": "User Guide",
    "更新历史": "Update History",
    "关于": "About",
    "确定": "OK",

    # ---- 顶部状态灯 ----
    "未连接": "Not Connected",
    "未选择设备": "No Device Selected",
    "断开": "Disconnect",
    "空闲": "Idle",
    "扫描中...": "Scanning...",
    "连接中...": "Connecting...",
    "已连接": "Connected",

    # ---- 底部读数条 ----
    "bar|接收": "RX",
    "bar|发送": "TX",
    "%d 字节 / %d 包": "%d bytes / %d pkts",
    "%d 字节": "%d bytes",

    # ---- 左侧: 设备 ----
    "设备": "Devices",
    "自动搜索附近设备，双击卡片可直接连接":
        "Auto-scans nearby devices; double-click a card to connect",
    "名称过滤": "Name Filter",
    "按名称或地址过滤…": "Filter by name or address…",
    "尚未发现设备\n正在自动搜索附近的 BLE 设备…":
        "No devices found yet\nScanning for nearby BLE devices…",
    "连接": "Connect",

    # ---- 左侧: 服务与特征 ----
    "服务与特征": "Services & Characteristics",
    "连接后自动识别读写特征": "Read/Write characteristics auto-detected after connect",
    "属性": "Properties",
    "服务": "Service",
    "写入": "Write",
    "通知": "Notify",
    "应用特征设置": "Apply Characteristics",

    # ---- 右侧: 监视屏 ----
    "接收监视": "Monitor",
    "混合": "Mixed",
    "解码": "Decode",
    "转义": "Escapes",
    "超时时间": "Timeout",
    "同一帧被拆成多包时, 静默此时间后合并为一行显示; 0=每包一行":
        "Packets arriving within this quiet gap are merged into one line; 0 = one line per packet",
    "自动滚动": "Auto Scroll",
    "回显发送": "Echo TX",
    "自动日志": "Auto Log",
    "清空": "Clear",

    # ---- 右侧: 发送 ----
    "发送": "Send",
    "HEX 字节可用空格分隔": "HEX bytes may be separated by spaces",
    "发 送": "Send",
    "格式": "Format",
    "编码": "Encoding",
    "行尾": "Line End",
    "无": "None",
    "定时发送(ms)": "Timed Send (ms)",
    "开始定时": "Start Timed",
    "停止定时": "Stop Timed",
    "使用当前输入框内容, 可随时修改": "Uses current input text; editable anytime",
    "预设命令": "Preset Commands",
    "点「发」按当前格式快速发送": "Click \"Send\" to transmit with the current format",
    "mini|发": "Send",

    # ---- 对话框 ----
    "提示": "Notice",
    "接收区没有可保存的内容": "Nothing to save in the receive area",
    "保存日志": "Save Log",
    "文本文件 (*.txt);;所有文件 (*)": "Text files (*.txt);;All files (*)",
    "完成": "Done",
    "日志已保存到:\n%s": "Log saved to:\n%s",
    "保存失败": "Save Failed",
    "发送格式错误": "Send Format Error",
    "第 %d 条: %s": "Item %d: %s",
    "错误": "Error",
    "定时周期需为不小于 50 的整数(毫秒)":
        "Period must be an integer (ms) no less than 50",
    "请先选择写入特征和通知特征":
        "Please select the write and notify characteristics first",

    # ---- 帮助 / 关于 ----
    "1. 给蓝牙模块上电, 打开程序(自动持续扫描)\n"
    "2. 在左侧列表选中你的模块(可按名称过滤), 双击卡片连接\n"
    "3. 连接后自动识别读写特征(支持 HC-04/HM-10、NUS、ISSC 及自定义)\n"
    "4. 在输入框填写命令, 选择格式(ASCII/HEX)和行尾, 点【发送】\n"
    "5. MCU 的回复会实时显示在监视屏\n\n"
    "提示:\n"
    " - BLE 链路没有波特率概念, 波特率只在模块<->MCU 串口间有效\n"
    " - 定时发送可做周期轮询; 预设命令可快速重复发送\n"
    " - 菜单【工具】可切换浅色/深色主题\n"
    " - 详细说明见同目录 使用说明.md":
        "1. Power on the BLE module and launch the app (auto-scans continuously)\n"
        "2. Pick your module in the left list (filter by name), double-click to connect\n"
        "3. Read/Write characteristics are auto-detected after connect "
        "(HC-04/HM-10, NUS, ISSC and custom)\n"
        "4. Type a command, choose format (ASCII/HEX) and line ending, click [Send]\n"
        "5. MCU replies appear on the monitor in real time\n\n"
        "Tips:\n"
        " - BLE has no baud rate; baud rate only applies between module and MCU UART\n"
        " - Timed send works for periodic polling; presets speed up repeated sends\n"
        " - Menu [Tools] switches Light/Dark theme and language\n"
        " - See 使用说明.md in this folder for details",
    "%s V%s\n\n电脑BLE ↔ 模块 ↔ MCU 无线串口调试工具\n"
    "自动识别 HC-04/HM-10/NUS 等常见透传服务\n"
    "界面: PySide6(Qt)   通信: bleak":
        "%s V%s\n\nPC BLE ↔ Module ↔ MCU wireless serial debug tool\n"
        "Auto-detects common transparent services (HC-04/HM-10/NUS, ...)\n"
        "UI: PySide6(Qt)   Comm: bleak",
    "V1.1.1 (2026.10.19)\n"
    "- 修正下拉功能: 列表顺序固定, 弹层贴框下沿展开不遮挡门脸\n"
    "- 特征下拉应用失败自动回退\n"
    "- 新增解码选择与超时时间拼包显示\n"
    "- 图片资源归入 assets/ 目录\n\n"
    "V1.1 (2026.10.17)\n"
    "- 第一版":
        "V1.1.1 (2026.10.19)\n"
        "- Dropdown fix: fixed list order; popup opens below without covering the box\n"
        "- Characteristic dropdown auto-rolls back when apply fails\n"
        "- Decode option and timeout coalescing display\n"
        "- Image assets moved into assets/\n\n"
        "V1.1 (2026.10.17)\n"
        "- First release",

    # ---- 顶栏复制标签 ----
    "点击拖动选中文字后 Ctrl+C 复制；双击一键复制；右键更多选项":
        "Drag to select, Ctrl+C to copy; double-click copies all; right-click for more",
    "复制选中内容": "Copy Selection",
    "复制名称和 MAC": "Copy Name & MAC",
    "已复制: %s": "Copied: %s",

    # ---- 收发/操作日志 ----
    "[操作] 正在连接 %s (%s) ...": "[Action] Connecting to %s (%s) ...",
    "[错误] %s": "[Error] %s",
    "已连接，等待收发数据…<br>MCU 的回复将实时显示在这里":
        "Connected — waiting for data…<br>MCU replies will appear here in real time",
    "请在左侧选择设备并点击「连接」<br>连接后即可在此实时查看收发数据":
        "Select a device on the left and click [Connect]<br>"
        "Traffic will appear here in real time",

    # ---- 日志文件头 ----
    "===== 坤坤蓝牙助手日志 %s =====": "===== 坤坤蓝牙助手 Log %s =====",
    "===== %s 会话开始 =====": "===== Session start %s =====",
    "===== %s 会话结束 =====": "===== Session end %s =====",

    # ---- ble_engine: 引擎日志 ----
    "扫描出错: %s": "Scan error: %s",
    "连接失败: %s": "Connect failed: %s",
    "[断开] 远端设备已断开(断电或超出范围)":
        "[Disconnected] Remote device disconnected (power-off or out of range)",
    "[断开] 远端无响应(断电或超出范围), 已断开":
        "[Disconnected] No response from remote (power-off or out of range)",
    "[提示] 识别到自定义透传特征 %s (写入/通知共用同一特征, 已自动选择)":
        "[Hint] Custom transparent characteristic %s detected (shared write/notify, auto-selected)",
    "[提示] 未识别到已知透传服务, 已自动选择: 写入=%s 通知=%s (可在左侧手动修改)":
        "[Hint] No known transparent service found; auto-selected write=%s notify=%s "
        "(adjustable on the left)",
    "[提示] 已识别到 %s, 读写特征已自动配置":
        "[Hint] Detected %s; read/write characteristics configured",
    "[警告] 通知订阅失败: %s (可点[应用特征设置]重试)":
        "[Warning] Notify subscribe failed: %s (click [Apply Characteristics] to retry)",
    "[连接] 已连接 %s, MTU=%s": "[Connect] Connected %s, MTU=%s",
    "发送失败: %s": "Send failed: %s",
    "定时发送已停止: %s": "Timed send stopped: %s",
    "指定的特征无效": "Specified characteristic is invalid",
    "[特征] 已手动应用 写入=%s 通知=%s": "[Chars] Manually applied write=%s notify=%s",
    "应用特征失败: %s": "Apply characteristics failed: %s",
    "[断开] %s": "[Disconnected] %s",
    "[断开] 已断开连接": "[Disconnected] Disconnected",
    "HEX 格式不正确: 需要偶数个十六进制字符, 例如: AA 55 01 0D 0A":
        "Invalid HEX: need an even number of hex digits, e.g. AA 55 01 0D 0A",
    "(未命名)": "(Unnamed)",
    "设备未暴露任何 GATT 服务": "Device exposes no GATT services",
    "未找到可用的写入/通知特征, 请在左侧手动指定":
        "No usable write/notify characteristic found; pick one manually on the left",
    "未连接或未设置写入特征": "Not connected or write characteristic not set",
    "写入特征缺少可写属性": "Write characteristic lacks a writable property",
    "Nordic UART 标准服务(NUS)": "Nordic UART Standard Service (NUS)",
    "HC-04/HM-10 透传服务(FFE0/FFE1)": "HC-04/HM-10 Transparent Service (FFE0/FFE1)",
    "ISSC 透传服务(49535343)": "ISSC Transparent Service (49535343)",

    # ---- KNOWN_UUIDS 显示名 ----
    "Nordic UART 服务": "Nordic UART Service",
    "RX 写入特征": "RX Write Characteristic",
    "TX 通知特征": "TX Notify Characteristic",
    "HC-04/HM-10 透传服务": "HC-04/HM-10 Transparent Service",
    "透传特征(写入/通知)": "Transparent Characteristic (Write/Notify)",
    "ISSC 透传服务": "ISSC Transparent Service",
    "ISSC 写入特征": "ISSC Write Characteristic",
    "ISSC 通知特征": "ISSC Notify Characteristic",
    "HC-04 搜索过滤服务(LUUID)": "HC-04 Scan Filter Service (LUUID)",
    "Generic Access 服务": "Generic Access Service",
    "Generic Attribute 服务": "Generic Attribute Service",
    "Device Information 服务": "Device Information Service",
    "设备名称特征": "Device Name Characteristic",
    "外观特征": "Appearance Characteristic",
}
