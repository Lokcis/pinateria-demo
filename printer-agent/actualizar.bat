@echo off
rem Actualiza el agente: trae el codigo nuevo (git pull) y las dependencias.
rem Despues hay que reiniciarlo: cierra su ventana y abre iniciar.bat (o reinicia el PC).
setlocal
cd /d "%~dp0"

where git >nul 2>&1 || (
  echo No se encontro git. Instalalo desde https://git-scm.com/download/win
  goto :error
)
if not exist ".venv\Scripts\python.exe" (
  echo Falta instalar el agente. Ejecuta primero instalar.bat
  goto :error
)

echo Rama actual:
git rev-parse --abbrev-ref HEAD
echo Descargando cambios...
git pull --ff-only || goto :error

echo Actualizando dependencias...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt || goto :error

echo.
echo Agente actualizado. Reinicialo para que use el codigo nuevo:
echo cierra la ventana del agente y abre iniciar.bat (o reinicia el PC si arranca con Windows).
pause
exit /b 0

:error
echo.
echo La actualizacion no termino. Revisa el mensaje de arriba (el agente actual no se modifico si git fallo).
pause
exit /b 1
