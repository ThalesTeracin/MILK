@echo off
cd /d C:\JARVIS
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\JARVIS\CORRIGIR_TELA_PRETA_WHISPER.ps1"
echo.
echo Correcao aplicada. O whisper-cli agora deve rodar oculto.
pause
