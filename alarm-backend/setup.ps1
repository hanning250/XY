# Copy SDK dependencies into alarm-backend/lib
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$sdkRoot = Split-Path -Parent $root
$demoDir = Join-Path $sdkRoot "Demo示例\5- Python开发示例\2-报警布防Demo"
$libDir = Join-Path $root "lib"

New-Item -ItemType Directory -Force -Path $libDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $root "data\pictures") | Out-Null

Copy-Item -Force (Join-Path $demoDir "HCNetSDK.py") (Join-Path $root "HCNetSDK.py")

$demoLib = Join-Path $demoDir "lib"
if (Test-Path $demoLib) {
    Copy-Item -Recurse -Force "$demoLib\*" $libDir
    Write-Host "Copied SDK files from demo lib folder."
} else {
    Write-Host "Demo lib folder not found, copying from SDK lib folder..."
    $sdkLib = Join-Path $sdkRoot "库文件"
    $files = @(
        "HCNetSDK.dll", "HCCore.dll", "hlog.dll", "hpr.dll", "zlib1.dll",
        "libcrypto-1_1-x64.dll", "libssl-1_1-x64.dll"
    )
    foreach ($file in $files) {
        Copy-Item -Force (Join-Path $sdkLib $file) $libDir
    }
    Copy-Item -Recurse -Force (Join-Path $sdkLib "HCNetSDKCom") $libDir
}

$config = Join-Path $root "config.json"
if (-not (Test-Path $config)) {
    Copy-Item -Force (Join-Path $root "config.example.json") $config
    Write-Host "Created config.json from config.example.json"
}

Write-Host "Setup complete."
Write-Host "Next steps:"
Write-Host "  1. Edit config.json"
Write-Host "  2. pip install -r requirements.txt"
Write-Host "  3. python main.py"
