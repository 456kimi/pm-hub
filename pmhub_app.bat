@echo off
rem ============================================================
rem PM-Hub app window launcher (ASCII only - do not add non-ASCII)
rem
rem Why this exists:
rem   The plain browser tab kept showing Streamlit error pages. Two real
rem   causes were found on 2026-11-10:
rem     1. the pythonw process dies and nothing restarts it
rem     2. editing a local module while the server is running makes the
rem        next rerun fail with ImportError (module cache is not reloaded)
rem   Fix 2 lives in dashboard.py (mtime based module reload).
rem   Fix 1 is here: every launch probes /_stcore/health first, and if the
rem   service is dead or unhealthy it is restarted before the window opens.
rem   So "it does not open" becomes "click the icon again".
rem
rem Privacy (owner hard rule): loopback only, never LAN/public.
rem ============================================================
setlocal
cd /d "H:\github\pm-hub"

set "PY=C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\pythonw.exe"
if not exist "%PY%" set "PY=C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
if not exist "%PY%" set "PY=C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\pythonw.exe"
if not exist "%PY%" set "PY=C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe"

call :is_healthy
if not errorlevel 1 goto :open

rem ---- unhealthy: clear the port (if something holds it) and start fresh ----
call "%~dp0stop_dashboard.bat" >nul 2>&1
echo [%date% %time%] app-launcher: (re)starting pm-hub dashboard >> dashboard.log
start "" "%PY%" run_dashboard_logged.py

for /l %%i in (1,1,45) do (
    call :is_healthy
    if not errorlevel 1 goto :open
    ping -n 2 127.0.0.1 >nul
)

echo [%date% %time%] app-launcher: FAILED to become healthy >> dashboard.log
echo.
echo PM-Hub did not start. Reason is in:
echo   H:\github\pm-hub\_dash_run.log
echo.
pause
exit /b 1

:open
set "EDGE=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE%" set "EDGE=C:\Program Files\Microsoft\Edge\Application\msedge.exe"
if exist "%EDGE%" (
    rem Standalone app window: no address bar, own taskbar entry.
    start "" "%EDGE%" --app=http://127.0.0.1:8501
    exit /b 0
)
set "CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if exist "%CHROME%" (
    start "" "%CHROME%" --app=http://127.0.0.1:8501
    exit /b 0
)
start "" "http://127.0.0.1:8501"
exit /b 0

:is_healthy
rem Streamlit answers "ok" on this endpoint only when the app really serves.
set "HEALTH="
for /f "usebackq delims=" %%r in (`curl -s -m 3 http://127.0.0.1:8501/_stcore/health`) do set "HEALTH=%%r"
if /i "%HEALTH%"=="ok" exit /b 0
exit /b 1
