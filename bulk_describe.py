# -*- coding: utf-8 -*-
"""
PM-Hub 应用台账批量补全。
策略（分层，避免一次性 679 次联网）：
  1. 离线知识库 + 正则启发式：覆盖运行库 / NVIDIA CUDA / Autodesk / Adobe /
     Office / 开发工具 / 浏览器 / 播放器 / 国产软件 / 游戏平台 / Windows 内置 /
     压缩·效率工具 / 基准测试 等可识别大类。
  2. web_cache.json：本助手通过联网检索得到的「名称 -> 用途/类别」结果，
     由脚本消费（断点续跑，不重复联网）。
  3. 仍然无法识别的写入 unresolved.json，留待后续联网批次处理 / 放弃。

所有补全只写 purpose + category，保留 desc_confirmed=False（AI 代拟待确认），
由老板在应用台账页批量确认。已手动填写 / 已确认 / 已处理过的条目会被跳过。
"""
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from pm_registry import apply_registry, read_registry

HUB = Path(__file__).resolve().parent
REG = HUB / "registry.json"
UNRESOLVED = HUB / "unresolved.json"
WEBCACHE = HUB / "web_cache.json"

# 规则顺序 = 优先级（具体在前，通用在后）。每条：(regex, 用途中文, 类别)
RULES = [
    # ---- 异常 / 模板残留 ----
    (r"^\$\{\{", "（注册表模板残留/异常条目，建议在「待整理清单」清理）", "other"),

    # ---- NVIDIA ----
    (r"nvidia.{0,15}(driver|驱动|geforce experience|studio|game ready)",
     "NVIDIA 显卡驱动程序，负责管理 GPU 与游戏/创作性能。", "system"),
    (r"nvidia|geforce|nsight|cuda|cublas|cufft|cusolver|cusparse|curand|cupti|cudart|nvtx|nvml|nvprof|compute sanitizer|nvshim",
     "NVIDIA CUDA 工具包组件（GPU 并行计算开发库/工具）。", "dev"),

    # ---- Microsoft Visual C++ / VS / .NET / SQL / Office / Windows SDK ----
    (r"visual c\+\+.{0,20}redistributable|microsoft visual c\+\+",
     "Microsoft Visual C++ 运行库（Redistributable），C++ 程序运行所需。", "system"),
    (r"microsoft visual studio|msvc|build tools for visual|developer command prompt for vs|developer powershell for vs|visual studio \d{4}|visual studio community|visual studio professional",
     "Microsoft Visual Studio IDE 及配套 C++ 构建工具。", "dev"),
    (r"\.net\b|dotnet",
     ".NET 运行时/开发框架，微软跨平台应用运行与开发基础。", "dev"),
    (r"sql server|sql native client|msodbc|oledb driver|sqlmetal|sql writer",
     "Microsoft SQL Server / 数据库相关组件。", "dev"),
    (r"microsoft office|office (20\d\d|365|standard|professional)|microsoft (word|excel|powerpoint|outlook|onenote|access|publisher|visio|project|skype for business)",
     "Microsoft Office 办公套件组件。", "office"),
    (r"windows sdk|windows app sdk|windbg|windows assessment|windows driver|windows kits|windows performance toolkit|debugging tools for windows|windows iot",
     "Windows 平台开发工具包 / SDK。", "dev"),
    (r"microsoft edge", "Microsoft Edge 网页浏览器。", "browser"),
    (r"microsoft teams|onedrive|skype|powertoys|windows terminal|microsoft to do|whiteboard|bing|microsoft maths|microsoft store",
     "Microsoft 官方应用/工具。", "tool"),
    (r"microsoft (.+)", "Microsoft 官方软件/组件。", "other"),

    # ---- Adobe ----
    (r"adobe|photoshop|illustrator|premiere|after effects|acrobat|lightroom|indesign|audition|dreamweaver|animate|substance|bridge|captivate",
     "Adobe 创意/多媒体制作软件。", "media"),

    # ---- Autodesk / CAD ----
    (r"autocad|autodesk|revit|inventor|maya|3ds max|civil 3d|fusion 360|dwg|object enabler",
     "Autodesk AutoCAD / 计算机辅助设计（CAD）软件。", "dev"),

    # ---- 开发语言 / 工具链 ----
    (r"python \d|python[ -][0-9]|idle \(python|py launcher|pip ",
     "Python 编程语言解释器/运行环境。", "dev"),
    (r"node\.js|npm|pnpm|yarn\b", "Node.js JavaScript 运行环境/包管理。", "dev"),
    (r"\bgit\b|git (bash|cmd|gui|release|extensions)", "Git 分布式版本控制系统。", "dev"),
    (r"github desktop|github cli|gh\b", "Git 代码托管/客户端工具。", "dev"),
    (r"rust\b|cargo\b|rustup", "Rust 编程语言工具链。", "dev"),
    (r"\bgo \d|golang|go[ -][0-9]", "Go 编程语言工具链。", "dev"),
    (r"java|jre|jdk|openjdk|adoptium|corretto|liberica", "Java 运行/开发环境。", "dev"),
    (r"cmake|mingw|gcc|msys2|llvm|clang\b|ninja\b|make\b", "C/C++ 编译与构建工具链。", "dev"),
    (r"docker|podman|kubernetes|kubectl|helm\b|minikube", "容器与编排工具。", "dev"),
    (r"visual studio code|vs code|code - insiders|vscode", "Visual Studio Code 代码编辑器。", "dev"),
    (r"intellij|pycharm|webstorm|clion|rider|jetbrains|android studio|eclipse|netbeans",
     "JetBrains / IDE 开发工具。", "dev"),
    (r"unity|unreal|godot|game engine|cryengine", "游戏引擎/开发工具。", "dev"),
    (r"powershell|conemu|windows terminal|terminal", "命令行/终端工具。", "dev"),
    (r"chocolatey|winget|scoop", "Windows 包管理器。", "dev"),
    (r"blender|zbrush|davinci|cinema 4d|houdini|substance painter",
     "3D / 影视制作软件。", "media"),

    # ---- 压缩 / 效率 / 文本工具 ----
    (r"7-zip|winrar|bandizip|peazip|360压缩|好压|winzip", "文件压缩/解压工具。", "tool"),
    (r"everything\b|listary|ditto|snipping|sharex|greenshot|screenpresso|powertoys|quicklook|ditto|ditto",
     "效率/桌面辅助工具。", "tool"),
    (r"notepad\+\+|sublime text|notepad--|emeditor|notepad3", "文本/代码编辑器。", "tool"),

    # ---- 影音播放 / 音乐 ----
    (r"vlc|potplayer|kmplayer|mpc[- ]|foobar|spotify|netease|网易云|qq音乐|酷狗|酷我|groove music|movies|sound recorder|audacity|goldwave",
     "影音播放/音乐客户端。", "media"),

    # ---- 浏览器 ----
    (r"chrome|firefox|brave|opera\b|vivaldi|arc browser|qq浏览器|360浏览器|搜狗浏览器|cent browser|chromium",
     "网页浏览器。", "browser"),

    # ---- 游戏平台 / 启动器 / 反作弊 ----
    (r"steam|epic games|epic launcher|ubisoft|blizzard|battle\.net|ea app|ea |gog galaxy|rockstar|riot|origin|bethesda|wegame|tencent wegame|xbox|game bar",
     "游戏平台/启动器。", "game"),
    (r"anticheatexpert|easyanticheat|battleye|denuvo|vac |tenprotect|ace anti",
     "游戏反作弊/版权保护系统。", "game"),

    # ---- 国产软件：细分（具体在前，兜底在后）----
    (r"360压缩|好压", "360 压缩——文件压缩/解压工具。", "tool"),
    (r"360安全卫士|安全卫士|火绒|腾讯电脑管家|金山毒霸", "安全防护/杀毒软件。", "security"),
    (r"wps|金山办公", "WPS Office——国产办公套件（文字/表格/演示）。", "office"),
    (r"腾讯会议|钉钉|飞书|企业微信|yy语音|oopz", "通讯/会议/协同软件。", "comm"),
    (r"微信|腾讯qq|qq\b", "即时通讯软件。", "comm"),
    (r"百度网盘|迅雷|小米云服务", "网盘/下载/云同步工具。", "download"),
    (r"输入法", "输入法。", "input"),
    (r"同花顺|东方财富|通达信|天天基金|股吧", "证券行情/交易软件。", "finance"),
    (r"哔哩哔哩|优酷|爱奇艺|腾讯视频|网易云|qq音乐|必剪", "音视频/内容平台客户端。", "media"),
    (r"腾讯元宝|豆包|智谱清言|千问|kimi|zcode|trae|qoder|ima", "AI 助手/编程工具。", "ai"),
    (r"米哈游|鹰角|完美世界|wegame", "游戏平台/启动器。", "game"),
    (r"360|腾讯|百度|阿里|网易|搜狗|夸克", "国产常用软件。", "tool"),

    # ---- 基准测试 ----
    (r"3dmark|cinebench|crystalmark|furmark|unigine|pcmark|geekbench|cpu-z|gpu-z|aida64|prime95",
     "硬件性能基准测试/监测工具。", "tool"),

    # ---- 杂项工具 ----
    (r"cheat engine", "内存修改/调试工具（游戏修改器）。", "tool"),
    (r"camtasia|obs|bandicam|录屏|screen recorder|snagit", "屏幕录制/视频制作工具。", "media"),
    (r"webcam|iriu|lumin|tether|camera|logi", "摄像头/影像工具。", "media"),
    (r"anytxt|everything|docfetcher|listary", "桌面搜索/文档检索工具。", "tool"),

    # ---- Windows 内置 ----
    (r"administrative tools|windows (tools|accessories|system|powershell|recovery|update|security|defender|memory diagnostic|hello|to do|sticky|snip|game|feedback hub|getting started|tips|support|maps|calendar|mail|photos|weather|alarms|voice recorder|camera|store|settings)|powershell ise|application verifier|component services|computer management|control panel|event viewer|disk cleanup|character map|magnify|narrator|sound recorder|steps recorder|snipping tool|paint|notepad|calculator|file explorer|command prompt|registry editor|task scheduler|xbox|game bar|your phone|phone link|groove|movies|voice recorder|weather|alarms|cortana|settings|store|snip & sketch|quick assist|remote desktop|windows sandbox",
     "Windows 系统内置工具/组件。", "system"),

    # ---- 通用兜底 ----
    (r"driver|驱动|固件", "硬件/设备驱动程序。", "system"),
    (r"redistributable|vcredist|运行库|可再发行", "软件运行所需运行库/可再发行组件。", "system"),
    (r"sdk|软件开发工具包", "软件开发工具包（SDK）。", "dev"),
    (r"runtime|运行时", "软件运行所需的运行时组件。", "system"),
    (r"benchmark|基准", "性能基准测试工具。", "tool"),
]

# 精确词典：覆盖 AI 工具 / 国产软件 / 具体游戏与开发组件等可识别项。
# (匹配串小写, 用途中文, 类别, 模式)  模式: 'sub'=包含, 'exact'=全等
CURATED = [
    # ---- AI 工具 ----
    ("kimi", "Kimi 智能助手（月之暗面 AI 对话工具）。", "ai", "sub"),
    ("workbuddy", "WorkBuddy AI 编程/办公助手客户端。", "ai", "sub"),
    ("opencode", "OpenCode——开源 AI 编程 Agent（终端 IDE）。", "ai", "sub"),
    ("qoder", "Qoder——AI 编程 IDE（阿里通义出品）。", "ai", "sub"),
    ("trae", "Trae——AI 编程 IDE（字节跳动出品）。", "ai", "sub"),
    ("千问", "通义千问——阿里 AI 对话助手。", "ai", "sub"),
    ("智谱清言", "智谱清言——智谱 AI 对话助手。", "ai", "sub"),
    ("豆包", "豆包——字节跳动 AI 对话助手。", "ai", "sub"),
    ("ima", "ima——腾讯 AI 知识库/智能工作台。", "ai", "sub"),
    ("ollama", "Ollama——本地大模型（LLM）运行与管理工具。", "ai", "sub"),
    ("voicestudio", "VoiceStudio——AI 语音/声音处理工具。", "ai", "sub"),
    # ---- 国产软件 / 工具 ----
    ("火绒", "火绒安全软件——国产杀毒/系统安全工具。", "tool", "sub"),
    ("uu加速器", "网易 UU 游戏加速器。", "tool", "sub"),
    ("uu远程", "网易 UU 远程桌面工具。", "tool", "sub"),
    ("飞书", "飞书——字节企业协作办公套件。", "tool", "sub"),
    ("小米云服务", "小米云服务客户端。", "tool", "sub"),
    ("miui+", "MIUI+——小米手机与 PC 协同工具。", "tool", "sub"),
    ("夸克", "夸克——阿里浏览器/效率工具。", "tool", "sub"),
    ("讯飞输入法", "讯飞输入法——语音输入法。", "tool", "sub"),
    ("米哈游启动器", "米哈游游戏启动器（原 miHoYo Launcher）。", "game", "sub"),
    ("鹰角启动器", "鹰角网络游戏启动器。", "game", "sub"),
    ("完美世界竞技平台", "完美世界游戏对战平台。", "game", "sub"),
    ("天天基金网", "天天基金网——基金行情/交易门户快捷方式。", "tool", "sub"),
    ("股吧", "股吧——东方财富炒股社区快捷方式。", "tool", "sub"),
    ("雷神加速器", "雷神游戏加速器。", "tool", "sub"),
    ("必剪", "必剪——B站视频剪辑工具。", "media", "sub"),
    ("图吧工具箱", "图吧工具箱——硬件检测/系统工具箱。", "tool", "sub"),
    ("游戏加加", "游戏加加——游戏帧率/硬件监控工具。", "tool", "sub"),
    ("软件管家", "软件管家——软件下载/管理工具。", "tool", "sub"),
    ("安全卫士", "（安全卫士类系统防护工具）。", "tool", "sub"),
    ("安全防护中心", "（安全防护中心入口）。", "tool", "sub"),
    ("网关客户端", "（企业网关/网络客户端）。", "tool", "sub"),
    ("项目管理", "（项目管理类软件入口）。", "tool", "sub"),
    ("vivo办公套件", "vivo 办公套件——手机与 PC 协同。", "tool", "sub"),
    ("vivo远控pc", "vivo 远控 PC——手机远程控制电脑。", "tool", "sub"),
    ("跨屏输入", "跨屏输入——手机/PC 跨屏输入工具。", "tool", "sub"),
    ("语音悬浮窗", "（语音助手悬浮窗入口）。", "tool", "sub"),
    ("意见反馈", "（软件意见反馈入口）。", "other", "sub"),
    ("参照管理器", "（文献/引用管理工具入口）。", "tool", "sub"),
    ("标准批处理检查器", "（批处理/脚本检查工具入口）。", "tool", "sub"),
    ("控制台 rar", "（WinRAR 中文帮助文档）。", "tool", "sub"),
    ("附着数字签名", "（数字签名工具入口）。", "tool", "sub"),
    ("配置工具", "（软件配置工具入口）。", "tool", "sub"),
    ("委托交易", "（证券委托交易快捷入口）。", "tool", "sub"),
    ("网页版交易", "（网页交易快捷入口）。", "tool", "sub"),
    ("卸载", "（该软件的卸载入口，非独立应用）。", "other", "sub"),
    ("解除安装", "（该软件的卸载入口，非独立应用）。", "other", "sub"),
    ("进入安装目录", "（打开安装目录的辅助入口）。", "other", "sub"),
    ("将设置重置", "（重置设置的辅助入口）。", "other", "sub"),
    ("重置设置", "（重置设置的辅助入口）。", "other", "sub"),
    ("最新版本的更新", "（更新程序的辅助入口）。", "other", "sub"),
    ("从早期版本进行移植", "（安装/迁移辅助入口）。", "other", "sub"),
    ("强力卸载", "（强力卸载工具入口）。", "tool", "sub"),
    ("设置", "（系统/软件设置入口）。", "other", "sub"),
    ("喜丧", "《喜丧》——国产独立游戏。", "game", "sub"),
    ("赛菲莉娅", "《赛菲莉娅》——国产独立游戏。", "game", "sub"),
    ("梦幻魔法公主", "《梦幻魔法公主》——国产独立游戏。", "game", "sub"),
    # ---- 系统 / 驱动 / 后台服务 ----
    ("amd software", "AMD 显卡驱动与软件控制中心（Adrenalin）。", "system", "sub"),
    ("amd install manager", "AMD 驱动/软件安装管理器。", "system", "sub"),
    ("intel", "Intel 驱动/软件组件（无线/蓝牙/芯片组）。", "system", "sub"),
    ("bluetooth", "Intel 无线蓝牙驱动组件。", "system", "sub"),
    ("optanedowngradeguard", "Intel Optane 降级保护组件。", "system", "sub"),
    ("rstdowngradeguard", "Intel RST 降级保护组件。", "system", "sub"),
    ("apple mobile device support", "Apple 移动设备支持（iTunes/iOS 驱动）。", "system", "sub"),
    ("bonjour", "Apple Bonjour 网络发现服务。", "system", "sub"),
    ("openal", "OpenAL——跨平台 3D 音频 API 运行库。", "system", "sub"),
    ("faro ls", "FARO 激光扫描仪驱动/配置工具。", "system", "sub"),
    ("lumix", "松下 LUMIX 相机联机/控制软件。", "media", "sub"),
    ("flydigispace", "飞智手柄配置工具。", "tool", "sub"),
    ("razer", "雷蛇 Razer Synapse 外设驱动/配置中心。", "tool", "sub"),
    ("rivatuner statistics server", "RivaTuner 帧率监控/OSD 工具（常配合 MSI Afterburner）。", "tool", "sub"),
    ("moonlight", "Moonlight——NVIDIA GameStream 串流客户端。", "tool", "sub"),
    ("ps remote play", "PlayStation Remote Play——PS 远程串流工具。", "tool", "sub"),
    ("chiaki-ng", "chiaki-ng——PS 开源远程串流客户端。", "tool", "sub"),
    ("sunshine", "Sunshine——开源游戏串流服务端（GameStream 替代）。", "tool", "sub"),
    ("playnite", "Playnite——游戏库统一管理启动器。", "game", "sub"),
    ("wallpaper engine", "Wallpaper Engine——动态壁纸工具。", "tool", "sub"),
    ("live2dviewerex", "Live2DViewerEX——Live2D 桌宠/看板娘工具。", "tool", "sub"),
    ("sakurafrp", "SakuraFrp——内网穿透/隧道工具。", "tool", "sub"),
    ("kaspersky password manager", "卡巴斯基密码管理器。", "tool", "sub"),
    ("wemod", "WeMod——游戏修改器平台。", "game", "sub"),
    ("wand", "Wand——WeMod 游戏修改器伴侣工具。", "game", "sub"),
    ("pandoc", "Pandoc——文档格式转换命令行工具。", "dev", "sub"),
    ("ubuntu", "Ubuntu OOS——WSL2 Linux 发行版（量化研究用）。", "dev", "sub"),
    ("wsl", "Windows Subsystem for Linux——Linux 子系统。", "dev", "sub"),
    ("soundwire server", "SoundWire——音频串流服务端。", "media", "sub"),
    ("wo mic client", "WO Mic——手机麦克风转 PC 工具。", "media", "sub"),
    ("microsoft pc health check", "Windows 11 电脑健康状况检查工具。", "system", "sub"),
    ("windows 11 安装助手", "Windows 11 安装助手。", "system", "sub"),
    ("电脑健康状况检查", "Windows 电脑健康状况检查工具。", "system", "sub"),
    ("voiceaccess", "Windows 语音访问（Voice Access）辅助功能。", "system", "sub"),
    ("livecaptions", "Windows 实时字幕（Live Captions）辅助功能。", "system", "sub"),
    ("oopz", "Oopz——第三方辅助/工具（具体用途待确认）。", "tool", "sub"),
    ("rabbitpro", "RabbitPro——第三方辅助/挂机工具（具体用途待确认）。", "tool", "sub"),
    ("zcode", "ZCode——未知应用（名称过短，待确认）。", "other", "sub"),
    ("nn", "nn——未知应用（名称过短，待确认）。", "other", "exact"),
    ("website", "（软件官网/帮助链接入口）。", "other", "sub"),
    ("readme", "（软件说明文档入口）。", "other", "sub"),
    ("samples", "（Windows SDK 示例/文档入口）。", "dev", "sub"),
    ("documentation manager", "Windows SDK 文档管理组件。", "dev", "sub"),
    ("database compare", "Office/SQL 数据库比较工具。", "dev", "sub"),
    ("spreadsheet compare", "Office 表格比较工具。", "tool", "sub"),
    ("print management", "Windows 打印管理控制台。", "system", "sub"),
    ("iscsi initiator", "Windows iSCSI 发起程序。", "system", "sub"),
    ("memory diagnostics", "Windows 内存诊断工具。", "system", "sub"),
    ("system information", "Windows 系统信息工具（msinfo32）。", "system", "sub"),
    ("system configuration", "Windows 系统配置（msconfig）。", "system", "sub"),
    ("task manager", "Windows 任务管理器。", "system", "sub"),
    ("performance monitor", "Windows 性能监视器。", "system", "sub"),
    ("resource monitor", "Windows 资源监视器。", "system", "sub"),
    ("on-screen keyboard", "Windows 屏幕键盘。", "system", "sub"),
    ("speech recognition", "Windows 语音识别。", "system", "sub"),
    ("wordpad", "Windows 写字板。", "system", "sub"),
    ("recoverydrive", "Windows 恢复驱动器创建工具。", "system", "sub"),
    ("services", "Windows 服务管理控制台。", "system", "sub"),
    ("run", "Windows 运行对话框（快捷方式）。", "system", "exact"),
    ("safe mode", "Windows 安全模式入口。", "system", "sub"),
    ("dfrgui", "Windows 磁盘碎片整理工具。", "system", "sub"),
    ("security configuration management", "Windows 安全配置管理（SCM）。", "system", "sub"),
    ("es驻留程序", "（某软件常驻后台程序）。", "tool", "sub"),
    ("userrecall", "Windows Recall/用户回溯相关组件。", "system", "sub"),
    ("unload kernel module", "（内核模块卸载调试工具）。", "dev", "sub"),
    ("stop tradingagentscn", "TradingAgentsCN 量化研究停止脚本。", "dev", "sub"),
    ("start tradingagentscn", "TradingAgentsCN 量化研究启动脚本。", "dev", "sub"),
    ("tradingagentscn", "TradingAgentsCN——AI 量化交易研究框架。", "dev", "sub"),
    ("desktop overlay host", "（应用叠加层宿主进程）。", "system", "sub"),
    ("app recovery", "Windows 应用恢复/重置工具。", "system", "sub"),
    ("dynamic application loader", "Windows 应用动态加载宿主服务。", "system", "sub"),
    ("debuggable package manager", "Windows 可调试包管理器。", "dev", "sub"),
    ("diagnosticshub_collectionservice", "Visual Studio DiagnosticsHub 收集服务。", "dev", "sub"),
    ("kits configuration installer", "Windows SDK/Kits 配置安装组件。", "dev", "sub"),
    ("msi development tools", "MSI 相关开发工具组件。", "dev", "sub"),
    ("crt development", "Microsoft C Runtime (CRT) 开发组件。", "dev", "sub"),
    ("acad private", "AutoCAD 私有组件。", "dev", "sub"),
    ("aca & mep 2018 object enabler", "AutoCAD Architecture/MEP 对象启用器。", "dev", "sub"),
    ("office 16 click-to-run", "Microsoft Office 即点即用（Click-to-Run）组件。", "office", "sub"),
    ("office 遥测", "Office 遥测/诊断组件。", "office", "sub"),
    ("office 语言", "Office 语言包组件。", "office", "sub"),
    ("universal crt", "Microsoft Universal CRT 运行库。", "system", "sub"),
    ("winrt intellisense", "Windows Runtime (WinRT) IntelliSense 开发组件。", "dev", "sub"),
    ("windows software development kit", "Windows 软件开发工具包（SDK）。", "dev", "sub"),
    ("windows performance analyzer", "Windows Performance Analyzer 性能分析工具。", "dev", "sub"),
    ("windows performance recorder", "Windows Performance Recorder 录制工具。", "dev", "sub"),
    ("wptx64", "Windows Performance Toolkit (WPT) x64 组件。", "dev", "sub"),
    ("gpuview", "GPUView——GPU/CPU 活动可视化分析工具。", "dev", "sub"),
    ("odbc data sources", "ODBC 数据源管理器。", "dev", "sub"),
    ("visual studio installer", "Visual Studio Installer 安装器。", "dev", "sub"),
    ("visual studio 生成工具", "Visual Studio Build Tools 2022 构建工具。", "dev", "sub"),
    ("ue prerequisites", "Unreal Engine 运行前置组件。", "dev", "sub"),
    ("ue4 prerequisites", "Unreal Engine 4 运行前置组件。", "dev", "sub"),
    ("launcher prerequisites", "（游戏/应用启动器前置组件）。", "game", "sub"),
    ("vcpp_crt.redist.clickonce", "Visual C++ CRT ClickOnce 可再发行组件。", "system", "sub"),
    ("vs_coreeditorfonts", "Visual Studio 核心编辑器字体组件。", "dev", "sub"),
    ("vs_filetracker", "Visual Studio FileTracker 组件。", "dev", "sub"),
    ("vs_filehandler", "Visual Studio 文件处理程序组件。", "dev", "sub"),
    ("vs_githubprotocolhandler", "Visual Studio GitHub 协议处理组件。", "dev", "sub"),
    ("vs_minshell", "Visual Studio 最小外壳（MinShell）组件。", "dev", "sub"),
    ("vs_vswebprotocolselector", "Visual Studio Web 协议选择组件。", "dev", "sub"),
    ("vs_", "Visual Studio 安装组件（MSI）。", "dev", "sub"),
    ("winappdeploy", "Windows App 部署工具（WinAppDeployCmd）。", "dev", "sub"),
    ("windows app cert", "Windows App Certification Kit 应用认证工具包。", "dev", "sub"),
    ("uxp webview support", "Adobe UXP WebView 支持组件。", "media", "sub"),
    ("python launcher", "Python Launcher for Windows（py 命令）。", "dev", "sub"),
    ("npp development", "NVIDIA NPP 开发库（图像处理原语）。", "dev", "sub"),
    ("nvjpeg development", "NVIDIA nvJPEG 开发库（JPEG 编解码）。", "dev", "sub"),
    ("nvrtc development", "NVIDIA NVRTC 运行时编译库。", "dev", "sub"),
    ("nvvm development", "NVIDIA NVVM（LLVM 后端）开发库。", "dev", "sub"),
    ("libnvptxcompiler development", "NVIDIA PTX 编译器库。", "dev", "sub"),
    ("cuobjdump", "NVIDIA cuobjdump——CUDA 二进制工具。", "dev", "sub"),
    ("cuxxfilt", "NVIDIA cuxxfilt——CUDA 异常处理过滤工具。", "dev", "sub"),
    ("nvcc", "NVIDIA NVCC CUDA 编译器。", "dev", "sub"),
    ("nvprune", "NVIDIA nvprune——CUDA 设备代码裁剪工具。", "dev", "sub"),
    ("futuremark systeminfo", "Futuremark SystemInfo——基准测试系统信息组件。", "tool", "sub"),
    ("eastmoney", "东方财富桌面客户端。", "tool", "sub"),
    ("yy语音", "YY 语音——欢聚时代语音社交工具。", "tool", "sub"),
    ("yy9", "YY 9——YY 语音客户端。", "tool", "sub"),
    ("mi service", "小米 MiService 后台服务。", "tool", "sub"),
    ("miservice", "小米服务组件。", "tool", "sub"),
    ("lenovo hec agent", "联想 HEC 后台代理服务。", "system", "sub"),
    ("pc health check", "Windows PC 健康检测工具。", "system", "sub"),
    ("intel software installer", "Intel 软件安装器。", "system", "sub"),
    ("moekoe music", "MoeKoe Music——音乐播放客户端。", "media", "sub"),
    ("rocket of whispers", "《Rocket of Whispers》——文字冒险游戏。", "game", "sub"),
    ("rail route", "《Rail Route》——铁路调度模拟游戏。", "game", "sub"),
    # ---- 具体游戏标题 ----
    ("a.plague.tale.innocence", "《瘟疫传说：无罪》——动作冒险游戏（Steam 单机）。", "game", "sub"),
    ("atelier yumia", "《优米雅的炼金工房》——光荣特库摩炼金工房系列 RPG。", "game", "sub"),
    ("balatro", "Balatro——热门扑克牌构筑类 Roguelike 游戏。", "game", "sub"),
    ("battle chasers: nightwar", "《战斗狂潮：永夜》——回合制 RPG 游戏。", "game", "sub"),
    ("beat cop", "《巡警》——复古像素风侦探冒险游戏。", "game", "sub"),
    ("call to arms - gates of hell: ostfront", "《武装突袭：地狱之门-东线》——二战即时战术游戏。", "game", "sub"),
    ("counter-strike 2", "Counter-Strike 2（CS2）——Valve 竞技射击游戏。", "game", "sub"),
    ("crusader kings iii", "《十字军之王3》——Paradox 中世纪策略模拟游戏。", "game", "sub"),
    ("cuphead", "《茶杯头》——手绘卡通风格动作横版游戏。", "game", "sub"),
    ("cyberpunk 2077", "《赛博朋克2077》——CDPR 开放世界 RPG 游戏。", "game", "sub"),
    ("dark.souls.iii", "《黑暗之魂3》——FromSoftware 硬核动作 RPG。", "game", "sub"),
    ("deathcoming", "《死亡降临》——点击式解谜冒险游戏。", "game", "sub"),
    ("disco elysium", "《极乐迪斯科》——获奖叙事型 RPG 游戏。", "game", "sub"),
    ("gris", "《GRIS》——艺术风格平台解谜游戏。", "game", "sub"),
    ("helldivers", "《地狱潜兵》——Arrowhead 合作射击游戏。", "game", "sub"),
    ("hi-fi rush", "《完美音浪》——节奏动作游戏。", "game", "sub"),
    ("metro exodus", "《地铁：离去》——后末日 FPS 游戏。", "game", "sub"),
    ("metal gear solid delta", "《合金装备Δ 食蛇者》——Konami 重制动作潜行游戏。", "game", "sub"),
    ("monster hunter stories", "《怪物猎人 物语》——卡普空 RPG 游戏。", "game", "sub"),
    ("noita", "《Noita》——像素魔法 Roguelike 游戏。", "game", "sub"),
    ("overcooked! 2", "《煮糊了2》——合作烹饪游戏。", "game", "sub"),
    ("peak", "《PEAK》——多人登山合作生存游戏。", "game", "sub"),
    ("pubg: battlegrounds", "《绝地求生》——蓝洞大逃杀射击游戏。", "game", "sub"),
    ("reanimal", "《REANIMAL》——Tarsier 合作恐怖冒险游戏。", "game", "sub"),
    ("redlauncher", "REDlauncher——CDPR 游戏启动器。", "game", "sub"),
    ("running with rifles", "《Running with Rifles》——俯视角战争游戏。", "game", "sub"),
    ("sekiro", "《只狼：影逝二度》——FromSoftware 动作游戏。", "game", "sub"),
    ("severed steel", "《Severed Steel》—— FPS 游戏。", "game", "sub"),
    ("slay the princess", "《杀戮公主》——叙事选择冒险游戏。", "game", "sub"),
    ("slay the spire 2", "《杀戮尖塔2》——卡牌 Roguelike 游戏。", "game", "sub"),
    ("stardew valley", "《星露谷物语》——农场模拟 RPG 游戏。", "game", "sub"),
    ("stray", "《Stray》——猫主角冒险解谜游戏。", "game", "sub"),
    ("supersplit", "SuperSplit——本地分屏/小游戏工具。", "tool", "sub"),
    ("syrian warfare", "《叙利亚战争》——即时战术游戏。", "game", "sub"),
    ("this is the police 2", "《这是警察2》——策略冒险游戏。", "game", "sub"),
    ("untitled goose game", "《无题大鹅》——搞怪解谜游戏。", "game", "sub"),
    ("warno southag", "《战争游戏：红龙》南部战区——策略游戏。", "game", "sub"),
    ("yes, your grace", "《Yes, Your Grace》——国王决策叙事游戏。", "game", "sub"),
    ("明末：渊虚之羽", "《明末：渊虚之羽》——国产动作 RPG 游戏。", "game", "sub"),
    ("无限暖暖", "《无限暖暖》——叠纸换装开放世界游戏。", "game", "sub"),
    ("逸剑风云决", "《逸剑风云决》——国产武侠 RPG 游戏。", "game", "sub"),
    ("神界：原罪2", "《神界：原罪2》——Larian 回合制 RPG 游戏。", "game", "sub"),
    ("米塔 miside", "《米塔 MiSide》——恐怖冒险游戏。", "game", "sub"),
    ("绝世好武功", "《绝世好武功》——武侠 Roguelike 游戏。", "game", "sub"),
    ("洛克王国：世界", "《洛克王国：世界》——腾讯宠物冒险游戏。", "game", "sub"),
    ("深岩银河", "《深岩银河》——合作射击游戏。", "game", "sub"),
    ("深空梦里人", "《深空梦里人》——独立游戏。", "game", "sub"),
    ("潜水员戴夫", "《潜水员戴夫》——冒险经营游戏。", "game", "sub"),
    ("生化危机2 重制版", "《生化危机2 重制版》——卡普空生存恐怖游戏。", "game", "sub"),
    ("田园记", "《田园记》——模拟经营游戏。", "game", "sub"),
    ("疑案追声", "《疑案追声》——声音解谜游戏。", "game", "sub"),
    ("破门而入：行动小队", "《破门而入：行动小队》——战术潜入游戏。", "game", "sub"),
    ("神之天平", "《神之天平 ASTLIBRA》——动作 RPG 游戏。", "game", "sub"),
    ("轩辕剑叁", "《轩辕剑叁》——大宇国产 RPG。", "game", "sub"),
    ("轩辕剑叁外传", "《轩辕剑叁外传 天之痕》——大宇国产 RPG。", "game", "sub"),
    ("逃离鸭科夫", "《逃离鸭科夫》——生存游戏。", "game", "sub"),
    ("露玛岛", "《露玛岛》——模拟经营游戏。", "game", "sub"),
    ("铸时匠 clocker", "《铸时匠 Clocker》——解谜冒险游戏。", "game", "sub"),
    ("雨中冒险: 回归", "《雨中冒险：回归》—— Roguelike 动作游戏。", "game", "sub"),
    ("猛兽派对", "《猛兽派对》——多人休闲派对游戏。", "game", "sub"),
    ("末刀", "《末刀》——动作游戏。", "game", "sub"),
    ("远方：涌变暗潮", "《远方：涌变暗潮》——国产游戏。", "game", "sub"),
    ("下一站江湖Ⅱ", "《下一站江湖Ⅱ》——武侠 RPG 游戏。", "game", "sub"),
    ("东京股神 stonks-9800", "《东京股神 STONKS-9800》——炒股题材游戏。", "game", "sub"),
    ("云端掠影", "《云端掠影 Black Skylands》——开放世界游戏。", "game", "sub"),
    ("药剂工艺：炼金模拟器", "《药剂工艺：炼金模拟器》——炼金模拟游戏。", "game", "sub"),
    ("觅长生", "《觅长生》——国产修仙 RPG 游戏。", "game", "sub"),
    ("武士 零", "《武士 零》——动作砍杀游戏。", "game", "sub"),
    ("武装突袭3", "《武装突袭3》——Bohemia 军事模拟游戏。", "game", "sub"),
    ("异环", "《异环》——国产开放世界游戏。", "game", "sub"),
    ("山海旅人", "《山海旅人》——国产志怪冒险游戏。", "game", "sub"),
    ("paradox launcher", "Paradox 游戏启动器。", "game", "sub"),
    ("eastmoney", "东方财富桌面客户端。", "tool", "sub"),
    ("hoyoverse", "HoYoverse 启动器（原神/星穹铁道等）。", "game", "sub"),
    ("kuro", "库洛游戏启动器（鸣潮等）。", "game", "sub"),
    ("netease", "网易游戏/云音乐客户端。", "game", "sub"),
    ("mihoyo", "米哈游启动器。", "game", "sub"),
    # ---- Office 套件组件（Start Menu 裸名）----
    ("excel", "Microsoft Office Excel 电子表格组件。", "office", "sub"),
    ("powerpoint", "Microsoft Office PowerPoint 演示组件。", "office", "sub"),
    ("outlook", "Microsoft Office Outlook 邮件/日历组件。", "office", "sub"),
    ("onenote", "Microsoft Office OneNote 笔记组件。", "office", "sub"),
    ("access", "Microsoft Office Access 数据库组件。", "office", "sub"),
    ("publisher", "Microsoft Office Publisher 排版组件。", "office", "sub"),
    ("word", "Microsoft Office Word 文字处理组件。", "office", "exact"),
    # ---- SDK / 系统辅助入口 ----
    ("for desktop apps", "Windows SDK 文档/工具/示例组件。", "dev", "sub"),
    ("ea", "EA 游戏平台/启动器。", "game", "exact"),
    ("mozilla maintenance service", "Mozilla 维护服务（Firefox 后台更新）。", "system", "sub"),
    ("pageoffice", "PageOffice——国产 Web Office 中间件/控件。", "tool", "sub"),
    ("playstation", "PlayStation 配件驱动/配置工具。", "system", "sub"),
    ("vs script debugging", "Visual Studio 脚本调试组件。", "dev", "sub"),
    ("fax and scan", "Windows 传真和扫描组件。", "system", "sub"),
    ("media player", "Windows Media Player 媒体播放器。", "media", "sub"),
    ("windows subsystem for linux", "Windows Subsystem for Linux——Linux 子系统。", "dev", "sub"),
    ("尼尔", "《尼尔：机械纪元》——白金工作室动作 RPG 游戏。", "game", "sub"),
    ("打字通", "打字通——打字练习工具（官网快捷方式）。", "tool", "sub"),
    ("无畏契约", "《无畏契约》（Valorant）助手工具。", "game", "sub"),
    ("暴雪战网", "暴雪战网（Battle.net）——游戏平台/启动器。", "game", "sub"),
]

COMPILED = [(re.compile(p, re.IGNORECASE), purpose, cat) for p, purpose, cat in RULES]

CUR_COMPILED = []
for key, purpose, cat, mode in CURATED:
    if mode == "exact":
        CUR_COMPILED.append((re.compile(r"^" + re.escape(key) + r"$", re.IGNORECASE), purpose, cat))
    else:
        CUR_COMPILED.append((re.compile(re.escape(key), re.IGNORECASE), purpose, cat))

# Start Menu 常见「辅助/卸载入口」噪声（非独立软件）
HELPER_NOISE = [
    "卸载", "解除安装", "进入安装目录", "将设置重置", "重置设置", "最新版本的更新",
    "从早期版本进行移植", "强力卸载", "软件管家", "设置", "意见反馈", "参照管理器",
    "标准批处理检查器", "控制台 rar", "附着数字签名", "配置工具", "委托交易",
    "网页版交易", "安全卫士", "安全防护中心", "语音悬浮窗", "跨屏输入", "启动异环",
    "卸载异环", "卸载nn", "卸载vivo", "卸载米哈游", "卸载鹰角", "卸载yy语音", "卸载nn",
    "卸载游戏", "卸载火绒", "卸载网关", "卸载项目管理", "卸载nn",
]


def classify(name: str, source: str = ""):
    # 1) 精确词典优先
    for rx, purpose, cat in CUR_COMPILED:
        if rx.search(name or ""):
            return purpose, cat
    # 2) Start Menu 辅助入口噪声
    if source == "startmenu":
        nl = (name or "").lower()
        for h in HELPER_NOISE:
            if h in nl:
                return "（某应用附带的辅助/卸载入口，非独立软件）。", "other"
    # 3) 通用正则启发式
    for rx, purpose, cat in COMPILED:
        if rx.search(name or ""):
            return purpose, cat
    return None, None


def apply_web_cache(app, wc):
    """把网页缓存里的描述写进应用记录（就地修改并返回）。

    来源是网络检索结果，属于「AI 代拟」，必须保持 desc_confirmed=False 等老板确认。
    2026-11-10 修：此处原先把 desc_confirmed 置 True，等于把 AI 写的用途冒充成
    用户已确认的结论（web_cache.json 里就有"具体产品待确认"这类内容）。
    """
    app["purpose"] = wc["purpose"]
    app["category"] = wc.get("category", "other")
    app["auto_source"] = "web"
    app["auto_at"] = datetime.now().strftime("%Y-%m-%d")
    app["desc_confirmed"] = False
    return app


def main():
    reg = read_registry(REG)

    apps = reg.get("apps", [])
    web = {}
    if WEBCACHE.exists():
        try:
            web = json.loads(WEBCACHE.read_text(encoding="utf-8"))
        except Exception:
            web = {}

    n_total = len(apps)
    unresolved = []

    def app_key(a):
        return (a.get("id"), a.get("name"), a.get("source"))

    baseline_counts = Counter(app_key(a) for a in apps)
    proposals = {}
    for a in apps:
        name = a.get("name", "")
        # 已确认 / 已处理 / 手动填写 -> 跳过
        if a.get("desc_confirmed"):
            continue
        if a.get("auto_source"):
            continue
        if a.get("purpose"):
            continue

        purpose, cat = classify(name, a.get("source"))
        if purpose:
            a["purpose"] = purpose
            a["category"] = cat
            a["auto_source"] = "heuristic"
            a["auto_at"] = datetime.now().strftime("%Y-%m-%d")
            proposals[app_key(a)] = dict(a)
            continue

        # 命中 web_cache
        wc = web.get(name)
        if wc and wc.get("purpose"):
            apply_web_cache(a, wc)
            proposals[app_key(a)] = dict(a)
            continue

        unresolved.append({
            "id": a.get("id"),
            "name": name,
            "source": a.get("source"),
            "path": a.get("path") or a.get("exe"),
        })

    applied = {"heuristic": 0, "web": 0}

    def apply_descriptions(latest):
        current_counts = Counter(app_key(a) for a in latest.get("apps", []))
        for current in latest.get("apps", []):
            key = app_key(current)
            candidate = proposals.get(key)
            if (not candidate or baseline_counts[key] != 1 or current_counts[key] != 1
                    or current.get("desc_confirmed") or current.get("auto_source") or current.get("purpose")):
                continue
            for field in ("purpose", "category", "auto_source", "auto_at", "desc_confirmed"):
                if field in candidate:
                    current[field] = candidate[field]
            applied[candidate["auto_source"]] += 1

    import export_static
    result = apply_registry("bulk_describe(auto)", apply_descriptions, path=REG, export=export_static.export)
    current_by_key = {app_key(a): a for a in result.data.get("apps", [])}
    unresolved = [a for a in unresolved if app_key(a) in current_by_key
                  and not current_by_key[app_key(a)].get("purpose")
                  and not current_by_key[app_key(a)].get("desc_confirmed")]
    UNRESOLVED.write_text(json.dumps(unresolved, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"应用总数         : {n_total}")
    print(f"本次启发式补全   : {applied['heuristic']}")
    print(f"本次联网缓存补全 : {applied['web']}")
    print(f"仍待处理(写入unresolved.json): {len(unresolved)}")
    print(f"已确认描述数     : {sum(1 for a in result.data.get('apps', []) if a.get('desc_confirmed'))}")
    if result.export_error:
        print(f"台账已保存，静态导出失败，请单独重导: {result.export_error}")
    else:
        print("静态页已更新     : index.html")


if __name__ == "__main__":
    main()
