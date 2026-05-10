@echo off
setlocal

for /f "tokens=*" %%i in ('git describe --tags --abbrev=0 2^>nul') do set TAG=%%i
if "%TAG%"=="" set TAG=vdev
set VERSION=%TAG:~1%
echo ==> Version: %VERSION%

echo %VERSION%> version.txt

echo ==> Clean old artifacts
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist
if exist LiangtianAutoScript.spec del LiangtianAutoScript.spec

echo ==> Build
.venv\Scripts\pyinstaller.exe ^
    --onefile ^
    --windowed ^
    --name LiangtianAutoScript ^
    --icon assets\app.ico ^
    --add-data "assets;assets" ^
    --add-data "ui\web;ui\web" ^
    --hidden-import adbutils ^
    --hidden-import webview ^
    --collect-all webview ^
    --collect-all rapidocr_onnxruntime ^
    main.py
if errorlevel 1 goto :fail

echo ==> Write dist\config.yaml
(echo ui:& echo   port: 8080& echo emulators: []) > dist\config.yaml

echo ==> Copy version.txt to dist\
copy version.txt dist\version.txt >nul

echo ==> Create full ZIP
powershell -Command "Compress-Archive -Path dist\* -DestinationPath LiangtianAutoScript-v%VERSION%.zip -Force"

echo ==> Create patch ZIP (tasks + assets only)
if exist patch_tmp rmdir /s /q patch_tmp
mkdir patch_tmp\tasks
mkdir patch_tmp\assets
xcopy /s /e /y tasks\   patch_tmp\tasks\   >nul
xcopy /s /e /y assets\  patch_tmp\assets\  >nul
powershell -Command "Compress-Archive -Path patch_tmp\* -DestinationPath patch-v%VERSION%.zip -Force"
rmdir /s /q patch_tmp

echo.
echo Done!
echo   dist\LiangtianAutoScript.exe
echo   dist\config.yaml
echo   LiangtianAutoScript-v%VERSION%.zip
echo   patch-v%VERSION%.zip
goto :eof

:fail
echo Build failed!
exit /b 1
