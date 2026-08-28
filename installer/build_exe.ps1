# ATENÇÃO: este build ainda NÃO inclui models/ (148 MB) nem
# third_party/ (108 MB). O executável gerado sai sem o modelo do Whisper
# e sem o binário que o executa, ou seja, sem reconhecimento de voz.
# Nesta máquina isso não aparece, porque os arquivos existem em
# C:\JARVIS e os caminhos em config/local/whisper_local.json são
# absolutos. Resolver na fase que tratar de distribuição.

$ErrorActionPreference = "Stop"
Set-Location C:\JARVIS

python -m pip install --upgrade pyinstaller

if (-not (Test-Path ".\src\main.py")) {
    throw "src\main.py não encontrado."
}

pyinstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name "MILK" `
  --add-data "assets;assets" `
  --add-data "config;config" `
  .\src\main.py

Write-Host ""
Write-Host "Build concluído." -ForegroundColor Green
Write-Host "Executável:" -ForegroundColor Cyan
Write-Host "C:\JARVIS\dist\MILK\MILK.exe"
