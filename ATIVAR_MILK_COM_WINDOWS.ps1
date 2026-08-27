$ErrorActionPreference = "Stop"
$startup = [Environment]::GetFolderPath("Startup")
$cmd = Join-Path $startup "MILK_Presence.cmd"

@"
@echo off
cd /d C:\JARVIS
start "" /min pythonw.exe "C:\JARVIS\MILK_Presence.py"
"@ | Set-Content -Encoding ASCII $cmd

Write-Host "MILK Presence configurada para iniciar com o Windows." -ForegroundColor Green
Write-Host $cmd
