@echo off
rem PM-Hub dashboard stopper (ASCII only - do not add non-ASCII)
rem Finds the PID that actually owns 127.0.0.1:8501 and kills only that one.
cd /d "H:\github\pm-hub"

set "PID="
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /R /C:"127.0.0.1:8501 .*LISTENING"') do set "PID=%%p"

if "%PID%"=="" (
    echo pm-hub dashboard is not running ^(port 8501 free^).
    exit /b 0
)

echo Stopping pm-hub dashboard, PID=%PID%
echo [%date% %time%] stopper: killing PID %PID% >> dashboard.log
taskkill /PID %PID% /F
timeout /t 2 /nobreak >nul
exit /b 0
