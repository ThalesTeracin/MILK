$ErrorActionPreference = "SilentlyContinue"

Write-Host "Procurando processos antigos do whisper-cli..." -ForegroundColor Cyan

$targets = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -ieq "whisper-cli.exe" -or
    ($_.CommandLine -and $_.CommandLine -like "*whisper-cli.exe*")
}

foreach ($p in $targets) {
    Write-Host "Encerrando PID $($p.ProcessId)..." -ForegroundColor Yellow
    Stop-Process -Id $p.ProcessId -Force
}

Write-Host "OK - processos antigos encerrados." -ForegroundColor Green
Write-Host "O novo listener executa whisper-cli com CREATE_NO_WINDOW." -ForegroundColor Green
