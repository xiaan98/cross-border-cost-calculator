@echo off
title 跨境小生意 · 成本模拟计算器
cd /d "%~dp0"

rem ---- 找一个真正能跑的 Python（WindowsApps 里的商店占位程序不算）----
set "PY="
python -c "import sys" >nul 2>nul
if not errorlevel 1 set "PY=python"

if not defined PY (
    py -3 -c "import sys" >nul 2>nul
    if not errorlevel 1 set "PY=py -3"
)

if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"

if not defined PY (
    echo [提示] 没有检测到可用的 Python。
    echo 注意：系统里那个 "python" 是 Microsoft Store 的占位程序，点了只会提示去商店安装，不是真正的 Python。
    echo 安装方式二选一：
    echo   1. 命令行运行：winget install Python.Python.3.12
    echo   2. 到 python.org 下载安装包，安装时勾选 "Add python.exe to PATH"
    echo 装好后重新双击本文件。
    echo.
    pause
    exit /b 1
)

rem ---- 检查依赖，缺了就自动装 ----
%PY% -c "import streamlit, pandas" >nul 2>nul
if errorlevel 1 (
    echo [首次运行] 正在安装依赖，大约需要一两分钟，请不要关闭本窗口……
    %PY% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [出错] 依赖安装失败。可手动执行：%PY% -m pip install -r requirements.txt
        pause
        exit /b 1
    )
)

echo.
echo ============================================
echo   计算器正在启动，浏览器会自动打开。
echo   用完后直接关闭本黑色窗口即可停止。
echo ============================================
echo.

%PY% -m streamlit run app.py --server.port 8501 --server.headless false

echo.
echo 服务已停止，按任意键关闭窗口。
pause >nul