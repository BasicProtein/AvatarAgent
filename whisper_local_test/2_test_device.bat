@echo off
chcp 65001 >nul
title Whisper GPU 测试 - AvatarAgent

echo =====================================================
echo   Whisper GPU 测试（使用独立 .venv）
echo =====================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [错误] 未找到本地 .venv，请先双击运行 1_setup_cuda.bat
    echo.
    pause & exit /b 1
)

echo 正在运行测试脚本...
echo.
.venv\Scripts\python.exe test_asr.py

echo.
pause
