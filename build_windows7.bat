@echo off
setlocal
cd /d "%~dp0"

set "ARCH=%~1"
if "%ARCH%"=="" set "ARCH=x86"

if /I "%ARCH%"=="x86" (
    set "PYTHON_SELECTOR=-3.8-32"
    set "LOCAL_PYTHON=.python38-x86\python.exe"
    set "VENV=.venv-win7-x86"
    set "DIST=dist_windows7_x86"
) else if /I "%ARCH%"=="x64" (
    set "PYTHON_SELECTOR=-3.8-64"
    set "LOCAL_PYTHON=.python38-x64\python.exe"
    set "VENV=.venv-win7-x64"
    set "DIST=dist_windows7_x64"
) else (
    echo Uso: build_windows7.bat x86
    echo   o: build_windows7.bat x64
    exit /b 2
)

if exist "%LOCAL_PYTHON%" (
    set "PYTHON=%LOCAL_PYTHON%"
) else (
    py %PYTHON_SELECTOR% -c "import sys; assert sys.version_info[:2] == (3, 8)" >nul 2>&1
    if errorlevel 1 (
        echo.
        echo ERROR: No se encontro Python 3.8 para %ARCH%.
        echo Instala Python 3.8 con la misma arquitectura y vuelve a ejecutar:
        echo   build_windows7.bat %ARCH%
        exit /b 1
    )
    set "PYTHON=py %PYTHON_SELECTOR%"
)

if not exist "%VENV%\Scripts\python.exe" (
    %PYTHON% -m venv "%VENV%"
    if errorlevel 1 exit /b 1
)

"%VENV%\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements-win7.txt
if errorlevel 1 exit /b 1

"%VENV%\Scripts\python.exe" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --noupx ^
    --name "TCP Client Hisense W7 %ARCH%" ^
    --distpath "%DIST%" ^
    --workpath "build_windows7_%ARCH%" ^
    --specpath "build_windows7_%ARCH%" ^
    --add-data "%~dp0..\WB+SNV2\HisenseLogo.png;." ^
    app.py
if errorlevel 1 exit /b 1

copy /Y "settings.ini" "%DIST%\settings.ini" >nul
copy /Y "LEEME_WINDOWS7.txt" "%DIST%\LEEME.txt" >nul
echo.
echo Compilacion terminada:
echo   %CD%\%DIST%\TCP Client Hisense W7 %ARCH%.exe
endlocal
