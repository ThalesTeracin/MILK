@echo off
cd /d C:\JARVIS
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\JARVIS\LIMPAR_MCP_TELA_PRETA.ps1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\JARVIS\CORRIGIR_INICIALIZACAO_MILK.ps1"
echo.
echo Correcao aplicada.
pause
