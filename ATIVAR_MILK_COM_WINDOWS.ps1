# =============================================================================
# SUBSTITUÍDO (Fase 3 - unificação de entry points, 2026-08-27).
# Este script registrava MILK_Presence.py (processo duplicado e superado)
# para iniciar via Startup do Windows. O mecanismo atual é uma Tarefa
# Agendada rodando src/main.py (processo único) -- ver
# installer\REGISTRAR_TAREFA_AGENDADA.ps1. NÃO execute este script: ele
# voltaria a rodar MILK_Presence.py em paralelo à Tarefa Agendada,
# causando disputa pelo mesmo microfone. O atalho .vbs que ele criava em
# Startup foi movido para installer\archive_startup\ (desativado).
# =============================================================================
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
