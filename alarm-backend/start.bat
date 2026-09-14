@echo off
REM 双击这个文件即可启动
REM 优先用 uv（本项目是 uv 项目，环境由 .\uv.lock 管），没有 uv 就退回 .venv
chcp 65001 >nul
cd /d "%~dp0"

set UV=
where uv >nul 2>nul && set UV=uv
if "%UV%"=="" (
    if exist "%APPDATA%\Python\Scripts\uv.exe" set UV=%APPDATA%\Python\Scripts\uv.exe
)

if not "%UV%"=="" (
    echo 使用 uv: %UV%
    "%UV%" run python start.py %*
    goto :done
)

echo [提示] 没找到 uv，改用本地 .venv
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" start.py %*
    goto :done
)

echo [提示] 本地没有 .venv。有 uv 的话执行: uv sync
echo        没有 uv 就执行: python -m venv .venv ^&^& .venv\Scripts\python.exe -m pip install -r requirements.txt
echo.
where py >nul 2>nul && (
    py start.py %*
    goto :done
)
where python >nul 2>nul && (
    python start.py %*
    goto :done
)

echo [错误] 找不到 Python，请先安装 Python 3.10+ 64 位版本
pause
exit /b 1

:done
echo.
echo 服务已退出。
pause
