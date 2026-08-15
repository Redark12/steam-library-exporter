@echo off
chcp 65001 >nul
title Steam 游戏库一键刷新
setlocal

set "PYEXE="
where py >nul 2>nul && set "PYEXE=py"
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
if not defined PYEXE where python >nul 2>nul && set "PYEXE=python"

if not defined PYEXE (
    echo [错误] 未找到 Python。请先安装 Python 3.10 以上版本，安装时勾选 "Add python.exe to PATH"。
    echo 如果已安装但运行后跳转微软商店，请到 设置 - 应用 - 高级应用设置 - 应用执行别名 里关闭 python 别名。
    pause
    exit /b 1
)

echo 使用 Python: %PYEXE%
echo.
%PYEXE% "%~dp0main.py"
echo.
pause
