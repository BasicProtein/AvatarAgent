@echo off
chcp 65001 >nul
title AutoDL SSH 隧道 - AvatarAgent

echo ================================================
echo   AutoDL SSH 隧道连接工具 - AvatarAgent
echo ================================================
echo.

REM ========== 请在此处填写 AutoDL 实例信息 ==========
REM 在 AutoDL 控制台 -> 实例详情 -> SSH 登录信息中查看
set AUTODL_HOST=connect.westc.gpuhub.com
set AUTODL_PORT=12345
set AUTODL_USER=root
REM 将 AutoDL 实例的 6006 端口映射到本地 6006 端口
set LOCAL_PORT=6006
set REMOTE_PORT=6006
REM ===================================================

echo [配置信息]
echo   AutoDL 主机: %AUTODL_HOST%:%AUTODL_PORT%
echo   端口映射:    本地 %LOCAL_PORT% -> 远程 %REMOTE_PORT%
echo   完成后访问:  http://127.0.0.1:%LOCAL_PORT%
echo.
echo [提示] 建立隧道后，在 AvatarAgent config.ini 中设置：
echo   [cloud_gpu]
echo   enabled = true
echo   api_url = http://127.0.0.1:%LOCAL_PORT%
echo.
echo 按任意键开始建立 SSH 隧道 (Ctrl+C 退出)...
pause >nul

echo.
echo [正在连接...] ssh -N -L %LOCAL_PORT%:127.0.0.1:%REMOTE_PORT% %AUTODL_USER%@%AUTODL_HOST% -p %AUTODL_PORT%
echo.

ssh -N -L %LOCAL_PORT%:127.0.0.1:%REMOTE_PORT% %AUTODL_USER%@%AUTODL_HOST% -p %AUTODL_PORT%

echo.
echo [隧道已断开]
pause
