"""CosyVoice setup and startup helpers."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from src.common.config_manager import ConfigManager
from src.common.logger import get_logger

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
COSYVOICE_DIR = PROJECT_ROOT / "third_party" / "CosyVoice"
COSYVOICE_SERVER_SCRIPT = COSYVOICE_DIR / "runtime" / "python" / "fastapi" / "server.py"
DEFAULT_MODEL_DIR = (
    PROJECT_ROOT / "third_party" / "models" / "modelscope_cache" / "hub" / "iic" / "CosyVoice2-0___5B"
)


def check_cosyvoice_installed() -> bool:
    return COSYVOICE_DIR.exists() and COSYVOICE_SERVER_SCRIPT.exists()


def clone_cosyvoice() -> bool:
    if check_cosyvoice_installed():
        logger.info("CosyVoice repository already exists.")
        return True

    third_party_dir = PROJECT_ROOT / "third_party"
    third_party_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "https://github.com/FunAudioLLM/CosyVoice.git",
                str(COSYVOICE_DIR),
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            logger.error("Failed to clone CosyVoice: %s", result.stderr)
            return False
        return True
    except subprocess.TimeoutExpired:
        logger.error("Cloning CosyVoice timed out.")
        return False
    except FileNotFoundError:
        logger.error("git is not available.")
        return False


def install_cosyvoice_deps() -> bool:
    if not check_cosyvoice_installed():
        logger.error("CosyVoice is not installed.")
        return False

    requirements = COSYVOICE_DIR / "requirements.txt"
    if not requirements.exists():
        logger.warning("requirements.txt not found, skipping dependency install.")
        return True

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements)],
            capture_output=True,
            text=True,
            timeout=600,
            cwd=str(COSYVOICE_DIR),
        )
        if result.returncode != 0:
            logger.error("Failed to install CosyVoice dependencies: %s", result.stderr)
            return False
        return True
    except subprocess.TimeoutExpired:
        logger.error("Installing CosyVoice dependencies timed out.")
        return False


def _get_cosyvoice_python() -> str:
    if sys.platform == "win32":
        venv_python = COSYVOICE_DIR / ".venv" / "Scripts" / "python.exe"
    else:
        venv_python = COSYVOICE_DIR / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _resolve_model_dir(config: ConfigManager) -> str:
    configured = config.get_cosyvoice_model_dir()
    if configured:
        return configured
    if DEFAULT_MODEL_DIR.exists():
        return str(DEFAULT_MODEL_DIR)
    return "iic/CosyVoice2-0.5B"


def _run_cosyvoice_python(code: str, timeout: int = 20) -> dict:
    python_exe = _get_cosyvoice_python()
    try:
        result = subprocess.run(
            [python_exe, "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(COSYVOICE_DIR),
        )
        if result.returncode != 0:
            return {
                "ok": False,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        payload = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "{}"
        data = json.loads(payload)
        data["ok"] = True
        return data
    except Exception as exc:
        return {"ok": False, "stderr": str(exc)}


def _build_runtime_probe_code(model_dir: str) -> str:
    safe_model_dir = json.dumps(model_dir)
    return f"""
import json
import os
from pathlib import Path

data = {{
    "torch_cuda_available": False,
    "gpu_name": None,
    "onnxruntime_gpu_installed": False,
    "onnxruntime_providers": [],
    "onnxruntime_cuda_session_ready": False,
    "onnxruntime_cuda_session_providers": [],
    "onnxruntime_cuda_error": "",
    "main_model_gpu_ready": False,
    "full_gpu_ready": False,
}}
model_dir = Path({safe_model_dir})
tokenizer_candidates = [
    model_dir / "speech_tokenizer_v3.onnx",
    model_dir / "speech_tokenizer_v2.onnx",
    model_dir / "speech_tokenizer_v1.onnx",
]

try:
    import torch
    data["torch_cuda_available"] = bool(torch.cuda.is_available())
    data["main_model_gpu_ready"] = data["torch_cuda_available"]
    if data["torch_cuda_available"]:
        data["gpu_name"] = torch.cuda.get_device_name(0)
    if os.name == "nt":
        torch_lib_dir = Path(torch.__file__).resolve().parent / "lib"
        if torch_lib_dir.exists():
            os.add_dll_directory(str(torch_lib_dir))
            os.environ["PATH"] = str(torch_lib_dir) + os.pathsep + os.environ.get("PATH", "")
except Exception as exc:
    data["onnxruntime_cuda_error"] = f"torch probe failed: {{exc}}"

try:
    import onnxruntime as ort

    providers = ort.get_available_providers()
    data["onnxruntime_providers"] = providers
    data["onnxruntime_gpu_installed"] = "CUDAExecutionProvider" in providers

    tokenizer_model = next((path for path in tokenizer_candidates if path.exists()), None)
    if data["onnxruntime_gpu_installed"] and tokenizer_model is not None:
        option = ort.SessionOptions()
        option.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        option.intra_op_num_threads = 1
        try:
            session = ort.InferenceSession(
                str(tokenizer_model),
                sess_options=option,
                providers=["CUDAExecutionProvider"],
            )
            session_providers = session.get_providers()
            data["onnxruntime_cuda_session_providers"] = session_providers
            data["onnxruntime_cuda_session_ready"] = "CUDAExecutionProvider" in session_providers
            if not data["onnxruntime_cuda_session_ready"]:
                data["onnxruntime_cuda_error"] = (
                    "CUDAExecutionProvider fell back to "
                    + ",".join(session_providers)
                )
        except Exception as exc:
            data["onnxruntime_cuda_error"] = str(exc)
    elif data["onnxruntime_gpu_installed"]:
        data["onnxruntime_cuda_error"] = "No speech_tokenizer onnx model found to probe."
except Exception as exc:
    data["onnxruntime_cuda_error"] = str(exc)

data["full_gpu_ready"] = (
    data["main_model_gpu_ready"] and data["onnxruntime_cuda_session_ready"]
)
data["can_use_gpu"] = data["main_model_gpu_ready"]
print(json.dumps(data, ensure_ascii=True))
"""


def get_cosyvoice_runtime_status() -> dict:
    config = ConfigManager()
    model_dir = _resolve_model_dir(config)
    code = _build_runtime_probe_code(model_dir)
    status = _run_cosyvoice_python(code)
    if not status.get("ok"):
        logger.warning("Failed to inspect CosyVoice runtime: %s", status.get("stderr", "unknown"))
        return {
            "torch_cuda_available": False,
            "gpu_name": None,
            "onnxruntime_gpu_installed": False,
            "onnxruntime_providers": [],
            "onnxruntime_cuda_session_ready": False,
            "onnxruntime_cuda_session_providers": [],
            "onnxruntime_cuda_error": status.get("stderr", "unknown"),
            "main_model_gpu_ready": False,
            "full_gpu_ready": False,
            "can_use_gpu": False,
        }
    status.pop("ok", None)
    return status


def start_cosyvoice(port: int = 50000, device: str | None = None) -> subprocess.Popen | None:
    if not check_cosyvoice_installed():
        logger.error("CosyVoice is not installed.")
        return None

    config = ConfigManager()
    host = config.get("cosyvoice", "host", "127.0.0.1")
    device_policy = (device or config.get_cosyvoice_device()).lower()
    if device_policy not in {"gpu", "cpu"}:
        device_policy = "gpu"

    python_exe = _get_cosyvoice_python()
    model_dir = _resolve_model_dir(config)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(COSYVOICE_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    cache_dir = PROJECT_ROOT / "third_party" / "models" / "modelscope_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    env["MODELSCOPE_CACHE"] = str(cache_dir)
    if device_policy == "cpu":
        env["CUDA_VISIBLE_DEVICES"] = "-1"
    else:
        env.pop("CUDA_VISIBLE_DEVICES", None)

    cmd = [
        python_exe,
        str(COSYVOICE_SERVER_SCRIPT),
        "--port",
        str(port),
        "--model_dir",
        model_dir,
        "--device",
        device_policy,
    ]

    logger.info(
        "Starting CosyVoice at http://%s:%s using %s (device=%s, model=%s)",
        host,
        port,
        python_exe,
        device_policy,
        model_dir,
    )

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(COSYVOICE_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(8)
        if proc.poll() is not None:
            stderr = proc.stderr.read().decode("utf-8", errors="ignore")
            logger.error("CosyVoice exited during startup: %s", stderr[:1000])
            return None
        return proc
    except Exception as exc:
        logger.error("Failed to start CosyVoice: %s", exc)
        return None


def check_cosyvoice_health(host: str = "127.0.0.1", port: int = 50000) -> bool:
    import urllib.error
    import urllib.request

    try:
        request = urllib.request.Request(f"http://{host}:{port}/docs", method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def setup_cosyvoice() -> bool:
    if not clone_cosyvoice():
        return False
    if not install_cosyvoice_deps():
        return False
    logger.info("CosyVoice setup complete.")
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="CosyVoice deployment helper")
    parser.add_argument("action", choices=["setup", "start", "check", "status"])
    parser.add_argument("--port", type=int, default=50000)
    parser.add_argument("--device", choices=["gpu", "cpu"], default=None)
    args = parser.parse_args()

    if args.action == "setup":
        sys.exit(0 if setup_cosyvoice() else 1)
    if args.action == "start":
        process = start_cosyvoice(port=args.port, device=args.device)
        if not process:
            sys.exit(1)
        try:
            logger.info("CosyVoice 服务已启动，PID=%s，按 Ctrl+C 停止", process.pid)
            process.wait()
        except KeyboardInterrupt:
            logger.info("正在停止 CosyVoice 服务...")
            process.terminate()
            process.wait(timeout=10)
        sys.exit(0)
    if args.action == "check":
        sys.exit(0 if check_cosyvoice_health(port=args.port) else 1)
    if args.action == "status":
        print(json.dumps(get_cosyvoice_runtime_status(), ensure_ascii=True, indent=2))
