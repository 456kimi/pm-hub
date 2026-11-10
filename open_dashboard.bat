@echo off
rem ============================================================
rem PM-Hub one-click launcher (ASCII only - do not add non-ASCII)
rem - starts the dashboard ONLY if it is not already running
rem - always opens the default browser at http://127.0.0.1:8501
rem - loopback only: never binds LAN/public IP
rem - uses pythonw.exe so NO black console window is left behind
rem - NO autostart / no scheduled task: owner explicitly declined it
rem ============================================================
cd /d "H:\github\pm-hub"

set "PY=C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\pythonw.exe"
if not exist "%PY%" set "PY=C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
if not exist "%PY%" set "PY=C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\pythonw.exe"
if not exist "%PY%" set "PY=C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe"

rem --- already running? just open the browser ---
netstat -ano | findstr /R /C:"127.0.0.1:8501 .*LISTENING" >nul
if not errorlevel 1 goto :open

rem --- not running: launch hidden ---
rem Streamlit params live in run_dashboard_logged.py, which also redirects
rem stdout/stderr to _dash_run.log (pythonw has no console, errors vanish otherwise).
echo [%date% %time%] launcher: starting pm-hub dashboard >> dashboard.log
start "" "%PY%" run_dashboard_logged.py

rem --- wait for readiness (max ~40s) then open ---
for /l %%i in (1,1,40) do (
    netstat -ano | findstr /R /C:"127.0.0.1:8501 .*LISTENING" >nul
    if not errorlevel 1 goto :open
    ping -n 2 127.0.0.1 >nul
)

echo [%date% %time%] launcher: FAILED - port 8501 did not come up >> dashboard.log
echo Startup failed. Check H:\github\pm-hub\dashboard.log
pause
exit /b 1

:open
start "" "http://127.0.0.1:8501"
exit /b 0
