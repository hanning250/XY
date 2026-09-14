# 拷贝 ISUP SDK 运行库到 alarm-backend/lib_isup
# 等价于 python setup_libs.py，这里只是为了习惯用 PowerShell 的场景。
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$python = $null
foreach ($candidate in @("..\.venv\Scripts\python.exe", "py", "python")) {
    if ($candidate -like "*\*") {
        if (Test-Path $candidate) { $python = (Resolve-Path $candidate).Path; break }
    } else {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($cmd) { $python = $cmd.Source; break }
    }
}

if (-not $python) {
    Write-Host "找不到 Python，请手动运行: python setup_libs.py" -ForegroundColor Red
    exit 1
}

Write-Host "使用 Python: $python"
& $python setup_libs.py
exit $LASTEXITCODE
