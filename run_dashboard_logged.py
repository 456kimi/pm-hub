# -*- coding: utf-8 -*-
"""run_dashboard_logged.py — pm-hub 看板后台启动包装
====================================================
目的：用 pythonw（无黑窗）启动时，Streamlit 的 stdout/stderr 默认丢失，
      一旦异常退出完全无法定位。本包装把两路输出落到 _dash_run.log，
      再走 streamlit 官方 CLI，参数与 open_dashboard.bat 完全一致。

用法：
    pythonw.exe run_dashboard_logged.py     # 生产用（无窗口）
    python.exe  run_dashboard_logged.py     # 排障用（有窗口）

口径（勿改，老板要求）：
    · 只监听 127.0.0.1，绝不暴露局域网/公网
    · gatherUsageStats=false，关闭 Streamlit 匿名遥测
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE, "_dash_run.log")

# 行缓冲追加写；父进程结束也不影响（这是独立文件句柄，不是管道）
_f = open(LOG, "a", encoding="utf-8", buffering=1)
sys.stdout = _f
sys.stderr = _f

import datetime

print("\n" + "=" * 60)
print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] wrapper start | pid={os.getpid()} | cwd={BASE}")

os.chdir(BASE)
sys.argv = [
    "streamlit", "run", "dashboard.py",
    "--server.headless", "true",
    "--server.port", "8501",
    "--server.address", "127.0.0.1",
    "--browser.gatherUsageStats", "false",
]

from streamlit.web import cli as stcli

code = stcli.main()
print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] wrapper exit code={code}")
sys.exit(code)
