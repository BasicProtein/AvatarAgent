@echo off
chcp 65001 >nul
title Whisper CUDA 环境安装（独立目录）

echo =====================================================
echo   Whisper 本地 GPU 环境安装
echo   显卡: RTX 3050  ^|  CUDA: 12.1
echo   安装位置: whisper_local_test\.venv  （独立，可删除）
echo =====================================================
echo.

REM 切换到 whisper_local_test 目录
cd /d "%~dp0"

REM ── Step 1: 创建独立虚拟环境 ─────────────────────────────────────────────────
echo [步骤 1/4] 创建独立虚拟环境 (.venv)...
if exist ".venv" (
    echo   已存在，跳过创建
) else (
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [错误] 创建虚拟环境失败，请确认 Python 已安装并在 PATH 中
        pause & exit /b 1
    )
    echo   创建成功 ✓
)
echo.

REM ── Step 2: 升级 pip ─────────────────────────────────────────────────────────
echo [步骤 2/4] 升级 pip...
.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
echo   完成 ✓
echo.

REM ── Step 3: 安装 PyTorch CUDA 12.1 ──────────────────────────────────────────
echo [步骤 3/4] 安装 PyTorch CUDA 12.1 版本...
echo   来源: https://download.pytorch.org/whl/cu121
echo   大小: 约 2.4 GB，请耐心等待...
echo.
.venv\Scripts\pip.exe install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
if %errorlevel% neq 0 (
    echo.
    echo [错误] PyTorch 安装失败！请检查网络连接后重试。
    pause & exit /b 1
)
echo   PyTorch CUDA 安装完成 ✓
echo.

REM ── Step 4: 安装 openai-whisper ──────────────────────────────────────────────
echo [步骤 4/4] 安装 openai-whisper...
.venv\Scripts\pip.exe install openai-whisper
if %errorlevel% neq 0 (
    echo [错误] openai-whisper 安装失败！
    pause & exit /b 1
)
echo   openai-whisper 安装完成 ✓
echo.

echo =====================================================
echo   [✓] 全部安装完成！
echo.
echo   下一步: 双击运行 2_test_device.bat
echo           验证 RTX 3050 + Whisper 是否正常工作
echo =====================================================
echo.
pause
