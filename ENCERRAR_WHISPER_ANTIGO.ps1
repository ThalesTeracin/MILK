$ErrorActionPreference = "SilentlyContinue"

$targets = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -ieq "whisper-cli.exe" -or
    ($_.CommandLine -and $_.CommandLine -like "*whisper-cli.exe*")
}

if (-not $targets) {
    Write-Host "Nenhum whisper-cli antigo rodando." -ForegroundColor Green
    exit 0
}

foreach ($p in $targets) {
    Write-Host "Encerrando whisper-cli PID $($p.ProcessId)" -ForegroundColor Yellow
    Stop-Process -Id $p.ProcessId -Force
}

Write-Host "Processos antigos encerrados." -ForegroundColor Green
