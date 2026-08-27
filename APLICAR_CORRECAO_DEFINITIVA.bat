@echo off
cd /d C:\JARVIS
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\JARVIS\ENCERRAR_WHISPER_ANTIGO.ps1"
python "C:\JARVIS\VERIFICAR_CORRECAO_TELA_PRETA.py"
echo.
echo Se aparecer LISTENER CORRIGIDO ESTA INSTALADO, feche esta janela e use a MILK.
pause
