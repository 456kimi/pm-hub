@echo off
rem PM-Hub dashboard launcher (ASCII only - do not add non-ASCII comments)
cd /d "H:\github\pm-hub"
set "PY=C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
if not exist "%PY%" set "PY=C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe"
rem Bind to loopback ONLY - never expose to LAN/public network (owner requirement).
rem gatherUsageStats=false disables Streamlit anonymous telemetry outbound.
"%PY%" -m streamlit run dashboard.py --server.headless true --server.port 8501 --server.address=127.0.0.1 --browser.gatherUsageStats false
