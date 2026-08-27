$startup = [Environment]::GetFolderPath("Startup")
$cmd = Join-Path $startup "MILK_Presence.cmd"
if (Test-Path $cmd) {
    Remove-Item $cmd -Force
}
Write-Host "Inicialização automática da MILK removida." -ForegroundColor Yellow
