@echo off
rem Arranca el agente de impresion (escucha en http://127.0.0.1:9100). No cierres esta ventana.
setlocal
cd /d "%~dp0"
title Agente de impresion - Pinateria Demo

if not exist ".venv\Scripts\python.exe" (
  echo Falta instalar el agente. Ejecuta primero instalar.bat
  pause
  exit /b 1
)

".venv\Scripts\python.exe" run.py

echo.
echo El agente se detuvo. Si no fue a proposito, revisa el mensaje de arriba.
pause
