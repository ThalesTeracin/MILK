@echo off
cd /d C:\JARVIS
python -m pip install -r requirements.txt
python -m playwright install chromium
pause
