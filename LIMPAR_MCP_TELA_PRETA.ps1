$ErrorActionPreference = "SilentlyContinue"

Write-Host "Procurando processos MCP antigos..." -ForegroundColor Cyan

$targets = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and (
        $_.CommandLine -like "*mock_mcp_server.py*" -or
        $_.CommandLine -like "*Testar_MCP.py*"
    )
}

foreach ($p in $targets) {
    Write-Host "Encerrando PID $($p.ProcessId): $($p.Name)" -ForegroundColor Yellow
    Stop-Process -Id $p.ProcessId -Force
}

Write-Host "Limpeza concluída." -ForegroundColor Green
