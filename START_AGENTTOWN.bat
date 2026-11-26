@echo off
setlocal
cd /d "%~dp0"
set "URL=http://127.0.0.1:8000"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$c=New-Object Net.Sockets.TcpClient; try{$c.Connect('127.0.0.1',8000);$c.Close();exit 0}catch{exit 1}" >nul 2>nul
if not errorlevel 1 (
  echo AgentTown is already running. Opening dashboard...
  start "" "%URL%"
  exit /b 0
)

where py >nul 2>nul
if not errorlevel 1 (
  start "AgentTown Server" /min cmd /k "cd /d ""%~dp0"" && py -3 app.py"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Python was not found.
    echo Install Python 3.9 or newer, then double-click this file again.
    pause
    exit /b 1
  )
  start "AgentTown Server" /min cmd /k "cd /d ""%~dp0"" && python app.py"
)

echo Waiting for AgentTown to start...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$end=(Get-Date).AddSeconds(30); do { $c=New-Object Net.Sockets.TcpClient; try{$c.Connect('127.0.0.1',8000);$c.Close();Start-Process '%URL%';exit 0}catch{$c.Close();Start-Sleep -Milliseconds 500} } while((Get-Date) -lt $end); exit 1"
if errorlevel 1 (
  echo AgentTown did not start. Check the minimized AgentTown Server window for errors.
  pause
  exit /b 1
)
endlocal
