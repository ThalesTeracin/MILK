@echo off
rem Abre a Milk sem janela de terminal.
rem
rem   Milk.bat            abre a Milk
rem   Milk.bat doutor     so o diagnostico, com a janela aberta
rem
rem Para ela subir junto com o Windows, use o menu do botao direito no
rem avatar: "Iniciar com o Windows".

cd /d "%~dp0"

if /I "%~1"=="doutor" (
    ".venv\Scripts\python.exe" milk.py doutor
    pause
    exit /b %errorlevel%
)

start "" ".venv\Scripts\pythonw.exe" milk.py
