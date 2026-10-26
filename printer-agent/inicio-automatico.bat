@echo off
rem Hace que el agente arranque solo al iniciar sesion en Windows (sin permisos de administrador).
rem   inicio-automatico.bat           -> activa
rem   inicio-automatico.bat quitar    -> desactiva
setlocal
set "ACCESO=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Agente de impresion Pinateria Demo.cmd"

if /i "%~1"=="quitar" (
  if exist "%ACCESO%" (
    del "%ACCESO%" && echo Inicio automatico desactivado.
  ) else (
    echo El inicio automatico no estaba activado.
  )
  pause
  exit /b 0
)

if not exist "%~dp0iniciar.bat" (
  echo No se encontro iniciar.bat junto a este archivo.
  pause
  exit /b 1
)

> "%ACCESO%" echo @start "Agente de impresion" /min "%~dp0iniciar.bat"
if errorlevel 1 (
  echo No se pudo crear el acceso en la carpeta de Inicio.
  pause
  exit /b 1
)
echo Listo: el agente arrancara minimizado cada vez que inicies sesion.
echo Si mueves la carpeta printer-agent, ejecuta este archivo de nuevo.
pause
