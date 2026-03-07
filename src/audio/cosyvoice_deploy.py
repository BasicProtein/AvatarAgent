"""CosyVoice 服务部署辅助脚本

提供 CosyVoice 语音合成服务的一键安装、启动、健康检查功能。
CosyVoice 项目：https://github.com/FunAudioLLM/CosyVoice
"""

import os
import subprocess
import sys
import time
from pathlib import Path

from src.common.logger import get_logger
from src.common.config_manager import ConfigManager

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
COSYVOICE_DIR = PROJECT_ROOT / "third_party" / "CosyVoice"


COSYVOICE_SERVER_SCRIPT = (
    COSYVOICE_DIR / "runtime" / "python" / "fastapi" / "server.py"
)


def check_cosyvoice_installed() -> bool:
    """检查 CosyVoice 是否已安装"""
    return COSYVOICE_DIR.exists() and (
        COSYVOICE_SERVER_SCRIPT.exists()
        or (COSYVOICE_DIR / "webui.py").exists()
    )


def clone_cosyvoice() -> bool:
    """克隆 CosyVoice 仓库

    Returns:
        是否成功
    """
    if check_cosyvoice_installed():
        logger.info("CosyVoice 已存在，跳过克隆")
        return True

    third_party_dir = PROJECT_ROOT / "third_party"
    third_party_dir.mkdir(parents=True, exist_ok=True)

    logger.info("正在克隆 CosyVoice 仓库...")
    try:
        result = subprocess.run(
            [
                "git", "clone", "--depth", "1",
                "https://github.com/FunAudioLLM/CosyVoice.git",
                str(COSYVOICE_DIR),
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            logger.error(f"CosyVoice 克隆失败: {result.stderr}")
            return False
        logger.info("CosyVoice 克隆成功")
        return True

    except subprocess.TimeoutExpired:
        logger.error("CosyVoice 克隆超时")
        return False
    except FileNotFoundError:
        logger.error("git 命令未找到，请先安装 git")
        return False


def install_cosyvoice_deps() -> bool:
    """安装 CosyVoice 依赖

    Returns:
        是否成功
    """
    if not check_cosyvoice_installed():
        logger.error("CosyVoice 未安装，请先执行 clone_cosyvoice()")
        return False

    req_file = COSYVOICE_DIR / "requirements.txt"
    if not req_file.exists():
        logger.warning("requirements.txt 未找到，跳过依赖安装")
        return True

    logger.info("正在安装 CosyVoice 依赖...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
            capture_output=True,
            text=True,
            timeout=600,
            cwd=str(COSYVOICE_DIR),
        )
        if result.returncode != 0:
            logger.error(f"CosyVoice 依赖安装失败: {result.stderr}")
            return False
        logger.info("CosyVoice 依赖安装成功")
        return True

    except subprocess.TimeoutExpired:
        logger.error("CosyVoice 依赖安装超时")
        return False


def _get_cosyvoice_python() -> str:
    """获取 CosyVoice 独立虚拟环境的 Python 路径

    CosyVoice 和 AvatarAgent 的依赖存在版本冲突（如 numpy），
    因此使用 third_party/CosyVoice/.venv 作为独立运行环境。
    若该 venv 不存在则回退到当前 Python。
    """
    if sys.platform == "win32":
        venv_python = COSYVOICE_DIR / ".venv" / "Scripts" / "python.exe"
    else:
        venv_python = COSYVOICE_DIR / ".venv" / "bin" / "python"

    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def start_cosyvoice(port: int = 50000) -> subprocess.Popen | None:
    """启动 CosyVoice 服务

    按优先级查找入口脚本:
    1. runtime/python/fastapi/server.py （官方 FastAPI 服务端）
    2. api.py （部分第三方封装）
    3. webui.py （Gradio WebUI，仅作兜底）

    Args:
        port: 服务端口，默认 50000（CosyVoice 官方默认端口）

    Returns:
        子进程对象（成功）或 None（失败）
    """
    if not check_cosyvoice_installed():
        logger.error("CosyVoice 未安装")
        return None

    config = ConfigManager()
    host = config.get("cosyvoice", "host", "127.0.0.1")

    candidates = [
        COSYVOICE_SERVER_SCRIPT,
        COSYVOICE_DIR / "api.py",
        COSYVOICE_DIR / "webui.py",
    ]
    entry_script = next((str(p) for p in candidates if p.exists()), None)
    if entry_script is None:
        logger.error("未找到 CosyVoice 入口脚本")
        return None

    python_exe = _get_cosyvoice_python()
    logger.info(
        f"正在启动 CosyVoice 服务: {host}:{port} "
        f"(脚本: {entry_script}, Python: {python_exe})"
    )

    try:
        env = os.environ.copy()
        cosyvoice_root = str(COSYVOICE_DIR)
        env["PYTHONPATH"] = (
            cosyvoice_root + os.pathsep + env.get("PYTHONPATH", "")
        )
        cache_dir = PROJECT_ROOT / "third_party" / "models" / "modelscope_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        env["MODELSCOPE_CACHE"] = str(cache_dir)

        cmd = [python_exe, entry_script, "--port", str(port)]

        proc = subprocess.Popen(
            cmd,
            cwd=cosyvoice_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        logger.info("等待 CosyVoice 服务启动...")
        time.sleep(15)

        if proc.poll() is not None:
            stderr = proc.stderr.read().decode("utf-8", errors="ignore")
            logger.error(f"CosyVoice 启动失败: {stderr[:500]}")
            return None

        logger.info(f"CosyVoice 服务已启动: http://{host}:{port}")
        return proc

    except Exception as e:
        logger.error(f"CosyVoice 启动异常: {e}")
        return None


def check_cosyvoice_health(host: str = "127.0.0.1", port: int = 50000) -> bool:
    """检查 CosyVoice 服务健康状态

    CosyVoice 官方 FastAPI 服务没有 /health 端点，
    通过访问 /docs（FastAPI 自动生成的 Swagger 页面）判断服务是否可达。

    Args:
        host: 服务地址
        port: 服务端口

    Returns:
        是否在线
    """
    import urllib.request
    import urllib.error

    url = f"http://{host}:{port}/docs"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def setup_cosyvoice() -> bool:
    """一键安装并配置 CosyVoice

    Returns:
        是否成功
    """
    logger.info("===== CosyVoice 一键部署 =====")

    # Step 1: 克隆
    if not clone_cosyvoice():
        return False

    # Step 2: 安装依赖
    if not install_cosyvoice_deps():
        return False

    logger.info("CosyVoice 部署完成！")
    logger.info(f"请使用以下命令启动: python -m src.audio.cosyvoice_deploy")
    logger.info(f"或在代码中调用: start_cosyvoice()")
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="CosyVoice 部署工具")
    parser.add_argument("action", choices=["setup", "start", "check"],
                        help="setup=一键安装, start=启动服务, check=健康检查")
    parser.add_argument("--port", type=int, default=50000, help="服务端口")
    args = parser.parse_args()

    if args.action == "setup":
        success = setup_cosyvoice()
        sys.exit(0 if success else 1)

    elif args.action == "start":
        proc = start_cosyvoice(port=args.port)
        if proc:
            try:
                print("CosyVoice 服务运行中，按 Ctrl+C 停止...")
                proc.wait()
            except KeyboardInterrupt:
                proc.terminate()
                print("\nCosyVoice 服务已停止")
        else:
            sys.exit(1)

    elif args.action == "check":
        online = check_cosyvoice_health(port=args.port)
        print(f"CosyVoice 服务状态: {'在线 ✅' if online else '离线 ❌'}")
        sys.exit(0 if online else 1)
