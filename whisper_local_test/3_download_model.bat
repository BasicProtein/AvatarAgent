@echo off
chcp 65001 >nul
title 下载 Whisper 模型 - IDM / 多线程

echo =====================================================
echo   Whisper turbo 模型下载
echo   方式 1: IDM（如已安装，自动调起）
echo   方式 2: 8 线程并发下载（IDM 未安装时使用）
echo =====================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [错误] 未找到本地 .venv，请先运行 1_setup_cuda.bat
    pause & exit /b 1
)

.venv\Scripts\python.exe download_model.py

echo.
pause
