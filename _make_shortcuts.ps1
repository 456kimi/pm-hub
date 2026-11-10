# Create the PM-Hub desktop shortcut only. (ASCII only)
# NOTE: autostart was explicitly REJECTED by the owner - do not re-add it here.
$ErrorActionPreference = 'Stop'
$lnkDir = 'H:\github\pm-hub'
$bat    = Join-Path $lnkDir 'open_dashboard.bat'
$pyIcon = 'C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe,0'

if (-not (Test-Path $bat)) { throw "missing $bat" }

$ws = New-Object -ComObject WScript.Shell
$desk = [Environment]::GetFolderPath('Desktop')
$lnkPath = Join-Path $desk 'PM-Hub Dashboard.lnk'
$s = $ws.CreateShortcut($lnkPath)
$s.TargetPath       = $bat
$s.WorkingDirectory = $lnkDir
$s.IconLocation     = $pyIcon
$s.Description      = 'Open PM-Hub dashboard (local only, 127.0.0.1:8501)'
$s.WindowStyle      = 7
$s.Save()
Write-Output "Desktop shortcut : $lnkPath"
Write-Output 'Done. Autostart intentionally NOT configured.'
