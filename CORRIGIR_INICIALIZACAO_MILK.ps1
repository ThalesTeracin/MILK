$ErrorActionPreference = "Stop"

$startup = [Environment]::GetFolderPath("Startup")
$oldCmd = Join-Path $startup "MILK_Presence.cmd"
$newVbs = Join-Path $startup "MILK_Presence.vbs"

if (Test-Path $oldCmd) {
    Remove-Item $oldCmd -Force
}

@'
Set shell = CreateObject("WScript.Shell")
shell.Run "cmd /c cd /d C:\JARVIS && pythonw.exe C:\JARVIS\MILK_Presence.py", 0, False
'@ | Set-Content -Encoding ASCII $newVbs

Write-Host ""
Write-Host "OK - Inicialização da MILK corrigida." -ForegroundColor Green
Write-Host "O antigo .cmd foi removido e substituído por launcher invisível .vbs." -ForegroundColor Cyan
Write-Host ""
Write-Host "Reinicie o Windows quando quiser validar." -ForegroundColor Yellow
