# 打包成单文件 .exe
# 第一次跑前: .venv\Scripts\pip install pyinstaller

$ErrorActionPreference = "Stop"

# 版本号从最近 tag 读取
$VERSION = (git describe --tags --abbrev=0 2>$null) -replace '^v',''
if (-not $VERSION) { $VERSION = "dev" }
Write-Host "==> 版本: $VERSION"

Write-Host "==> 写入 version.txt"
Set-Content version.txt $VERSION -Encoding utf8 -NoNewline

Write-Host "==> 清理旧产物"
if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path dist)  { Remove-Item dist  -Recurse -Force }
if (Test-Path LiangtianAutoScript.spec) { Remove-Item LiangtianAutoScript.spec -Force }

Write-Host "==> 打包"
$pyinst = ".venv\Scripts\pyinstaller.exe"
$pyArgs = @(
    "--onefile",
    "--windowed",
    "--name", "LiangtianAutoScript",
    "--icon", "assets\app.ico",
    "--add-data", "assets;assets",
    "--add-data", "ui\web;ui\web",
    "--hidden-import", "pywebio",
    "--hidden-import", "adbutils",
    "--hidden-import", "webview",
    "--collect-all", "pywebio",
    "--collect-all", "webview",
    "--collect-all", "rapidocr_onnxruntime",
    "main.py"
)
& $pyinst @pyArgs
if ($LASTEXITCODE -ne 0) { throw "pyinstaller failed" }

Write-Host "==> 写入默认 config.yaml 到 dist/"
"ui:`n  port: 8080`nemulators: []`n" | Set-Content dist\config.yaml -Encoding utf8

Write-Host "==> 复制 version.txt 到 dist/"
Copy-Item version.txt dist\version.txt

Write-Host "==> 打包 ZIP"
$ZIP = "LiangtianAutoScript-v$VERSION.zip"
Compress-Archive -Path dist\* -DestinationPath $ZIP -Force

Write-Host ""
Write-Host "成功！"
Write-Host "  dist\LiangtianAutoScript.exe"
Write-Host "  dist\config.yaml"
Write-Host "  dist\version.txt"
Write-Host "  $ZIP"
