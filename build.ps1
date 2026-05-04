# 打包成单文件 .exe
# 第一次跑前: pip install pyinstaller

$ErrorActionPreference = "Stop"

Write-Host "==> 清理旧产物" -ForegroundColor Cyan
if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path dist) { Remove-Item dist -Recurse -Force }
if (Test-Path LiangtianAutoScript.spec) { Remove-Item LiangtianAutoScript.spec -Force }

Write-Host "==> 打包" -ForegroundColor Cyan
pyinstaller `
    --onefile `
    --name LiangtianAutoScript `
    --add-data "assets;assets" `
    --hidden-import pywebio `
    --hidden-import adbutils `
    --collect-all pywebio `
    main.py

Write-Host "==> 复制 config.yaml 到 dist/" -ForegroundColor Cyan
Copy-Item config.yaml dist/

Write-Host ""
Write-Host "成功！产物在 dist/" -ForegroundColor Green
Write-Host "  - LiangtianAutoScript.exe"
Write-Host "  - config.yaml  (用户可编辑)"
