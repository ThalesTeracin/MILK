$ErrorActionPreference = "Stop"
Set-Location C:\JARVIS

python -m pip install --upgrade pyinstaller

if (-not (Test-Path ".\MILK_Command_Center.py")) {
    throw "MILK_Command_Center.py não encontrado."
}

pyinstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name "MILK" `
  --add-data "assets;assets" `
  --add-data "config;config" `
  .\MILK_Command_Center.py

Write-Host ""
Write-Host "Build concluído." -ForegroundColor Green
Write-Host "Executável:" -ForegroundColor Cyan
Write-Host "C:\JARVIS\dist\MILK\MILK.exe"
