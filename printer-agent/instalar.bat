@echo off
rem Instala el agente de impresion en este PC: entorno virtual, dependencias y .env.
rem Se ejecuta una sola vez (doble clic). Es seguro repetirlo.
setlocal
cd /d "%~dp0"

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
  where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo No se encontro Python 3. Instalalo desde https://www.python.org/downloads/
  echo y marca la casilla "Add python.exe to PATH". Luego ejecuta este archivo de nuevo.
  goto :error
)

if not exist ".venv\Scripts\python.exe" (
  echo Creando el entorno virtual...
  %PY% -m venv .venv || goto :error
)

echo Instalando dependencias...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt || goto :error

if not exist ".env" (
  copy ".env.example" ".env" >nul || goto :error
  echo.
  echo Se creo el archivo .env. Abrelo con el Bloc de notas y revisa:
  echo   AGENTE_MODO=escpos
  echo   AGENTE_IMPRESORA_WINDOWS=^<nombre exacto de la impresora en Windows^>
  echo   AGENTE_ORIGENES_PERMITIDOS=https://pos.demo.example.com,http://localhost:5173
) else (
  echo El archivo .env ya existe: no se toco.
)

echo.
echo Listo. Para arrancar el agente: iniciar.bat
echo Para que arranque solo al iniciar sesion en Windows: inicio-automatico.bat
pause
exit /b 0

:error
echo.
echo La instalacion no termino. Revisa el mensaje de arriba.
pause
exit /b 1
