@echo off
setlocal

set /p VERSION=<version.txt
echo ==> Patch version: %VERSION%

echo ==> Create patch ZIP
if exist patch_tmp rmdir /s /q patch_tmp
mkdir patch_tmp\tasks
mkdir patch_tmp\assets
xcopy /s /e /y tasks\   patch_tmp\tasks\   >nul
xcopy /s /e /y assets\  patch_tmp\assets\  >nul
powershell -Command "Compress-Archive -Path patch_tmp\* -DestinationPath patch-v%VERSION%.zip -Force"
rmdir /s /q patch_tmp

echo ==> Upload to release v%VERSION%
gh release upload v%VERSION% patch-v%VERSION%.zip --clobber

echo.
echo Done! patch-v%VERSION%.zip uploaded to v%VERSION%
