$ErrorActionPreference="Stop"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    winget install --id GitHub.cli -e --accept-package-agreements --accept-source-agreements
}

Write-Host ""
Write-Host "GitHub CLI instalado." -ForegroundColor Green
Write-Host "Agora rode:" -ForegroundColor White
Write-Host "gh auth login" -ForegroundColor Yellow
