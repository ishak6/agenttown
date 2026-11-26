@echo off
echo Stopping AgentTown on port 8000...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue ^| Select-Object -ExpandProperty OwningProcess -Unique; if($p){$p ^| ForEach-Object {Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue}; Write-Host 'AgentTown stopped.'}else{Write-Host 'No AgentTown server is listening on port 8000.'}"
pause
