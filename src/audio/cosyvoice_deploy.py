"""CosyVoice setup and startup helpers."""

from __future__ import annotations

import json
import os
import signal
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


def _list_cosyvoice_processes(port: int) -> list[dict]:
    if sys.platform == "win32":
        script = f"""
$pattern = 'runtime[\\\\/]+python[\\\\/]+fastapi[\\\\/]+server\\.py'
$items = Get-CimInstance Win32_Process |
    Where-Object {{
        $_.Name -eq 'python.exe' -and
        $_.CommandLine -match $pattern -and
        $_.CommandLine -match '--port\\s+{port}(\\s|$)'
    }} |
    Select-Object ProcessId, CommandLine
if (-not $items) {{
    '[]'
}} else {{
    $items | ConvertTo-Json -Compress
}}
"""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.warning("Failed to inspect CosyVoice processes: %s", result.stderr.strip())
                return []
            payload = result.stdout.strip() or "[]"
            data = json.loads(payload)
            if isinstance(data, dict):
                return [data]
            if isinstance(data, list):
                return data
        except Exception as exc:
            logger.warning("Failed to inspect CosyVoice processes: %s", exc)
        return []

    try:
        result = subprocess.run(
            ["ps", "-eo", "pid=,args="],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            logger.warning("Failed to inspect CosyVoice processes: %s", result.stderr.strip())
            return []

        matches: list[dict] = []
        port_token = f"--port {port}"
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            parts = stripped.split(None, 1)
            if len(parts) != 2:
                continue
            pid_text, command_line = parts
            normalized = command_line.replace("\\", "/")
            if "runtime/python/fastapi/server.py" not in normalized:
                continue
            if port_token not in command_line:
                continue
            matches.append({"ProcessId": int(pid_text), "CommandLine": command_line})
        return matches
    except Exception as exc:
        logger.warning("Failed to inspect CosyVoice processes: %s", exc)
        return []


def _terminate_process(pid: int) -> bool:
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                return True
            logger.warning("Failed to stop CosyVoice PID %s: %s", pid, result.stderr.strip())
            return False

        os.kill(pid, signal.SIGTERM)
        return True
    except ProcessLookupError:
        return True
    except Exception as exc:
        logger.warning("Failed to stop CosyVoice PID %s: %s", pid, exc)
        return False


def stop_cosyvoice(port: int = 50000) -> dict:
    processes = _list_cosyvoice_processes(port)
    stopped_pids: list[int] = []

    for process in processes:
        pid = int(process["ProcessId"])
        if _terminate_process(pid):
            stopped_pids.append(pid)

    host = ConfigManager().get("cosyvoice", "host", "127.0.0.1")
    deadline = time.time() + 20
    while time.time() < deadline:
        if not check_cosyvoice_health(host=host, port=port):
            break
        time.sleep(0.5)

    online = check_cosyvoice_health(host=host, port=port)
    if online:
        return {
            "status": "error",
            "stopped_pids": stopped_pids,
            "message": f"CosyVoice 服务未能在端口 {port} 上停止。",
        }

    if stopped_pids:
        return {
            "status": "success",
            "stopped_pids": stopped_pids,
            "message": f"已停止 CosyVoice 服务（PID: {', '.join(str(pid) for pid in stopped_pids)}）。",
        }

    return {
        "status": "success",
        "stopped_pids": [],
        "message": "CosyVoice 服务当前未在运行。",
    }


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
    # 禁止联网检查/下载模型；同时清除系统代理，防止 wetext/modelscope 尝试走代理联网
    env["MODELSCOPE_OFFLINE"] = "1"
    for proxy_key in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
        env.pop(proxy_key, None)
    env["NO_PROXY"] = "*"
    env["no_proxy"] = "*"
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
        log_path = PROJECT_ROOT / "logs" / "cosyvoice.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_file = open(log_path, "a", encoding="utf-8", buffering=1)
        proc = subprocess.Popen(
            cmd,
            cwd=str(COSYVOICE_DIR),
            env=env,
            stdout=log_file,
            stderr=log_file,
        )
        time.sleep(8)
        if proc.poll() is not None:
            log_file.close()
            stderr = log_path.read_text(encoding="utf-8", errors="ignore")[-1000:]
            logger.error("CosyVoice exited during startup: %s", stderr)
            return None
        return proc
    except Exception as exc:
        logger.error("Failed to start CosyVoice: %s", exc)
        return None


def restart_cosyvoice(port: int = 50000, device: str | None = None) -> dict:
    config = ConfigManager()
    host = config.get("cosyvoice", "host", "127.0.0.1")
    stop_result = stop_cosyvoice(port=port)
    if stop_result["status"] != "success":
        return stop_result

    proc = start_cosyvoice(port=port, device=device)
    if not proc:
        return {
            "status": "error",
            "stopped_pids": stop_result.get("stopped_pids", []),
            "message": "CosyVoice 服务启动失败，请检查日志。",
        }

    deadline = time.time() + 120
    while time.time() < deadline:
        if check_cosyvoice_health(host=host, port=port):
            stopped = stop_result.get("stopped_pids", [])
            stopped_text = (
                f"，已停止旧进程 {', '.join(str(pid) for pid in stopped)}"
                if stopped
                else ""
            )
            return {
                "status": "success",
                "pid": proc.pid,
                "stopped_pids": stopped,
                "message": f"CosyVoice 服务已重启，当前 PID={proc.pid}{stopped_text}。",
            }
        time.sleep(0.5)

    return {
        "status": "error",
        "pid": proc.pid,
        "stopped_pids": stop_result.get("stopped_pids", []),
        "message": f"CosyVoice 进程已启动（PID={proc.pid}），但端口 {port} 在超时内未就绪。",
    }


def check_cosyvoice_health(host: str = "127.0.0.1", port: int = 50000) -> bool:
    import urllib.error
    import urllib.request

    try:
        request = urllib.request.Request(f"http://{host}:{port}/docs", method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def update_cosyvoice_models() -> dict:
    """联网拉取 CosyVoice 所需模型的最新版本，仅在用户主动触发时调用。

    下载目标：
      - iic/CosyVoice2-0.5B（主模型）
      - pengzhendong/wetext（前端文本处理模型）

    所有模型缓存到项目内的 third_party/models/modelscope_cache，
    不写入 C 盘或系统用户目录。
    """
    python_exe = _get_cosyvoice_python()
    cache_dir = PROJECT_ROOT / "third_party" / "models" / "modelscope_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    model_dir = _resolve_model_dir(ConfigManager())
    code = f"""
import os, json, sys
os.environ["MODELSCOPE_CACHE"] = {json.dumps(str(cache_dir))}
os.environ.pop("MODELSCOPE_OFFLINE", None)

results = []
errors = []

try:
    from modelscope.hub.snapshot_download import snapshot_download
    snapshot_download("pengzhendong/wetext", cache_dir={json.dumps(str(cache_dir))})
    results.append("pengzhendong/wetext")
except Exception as e:
    errors.append(f"pengzhendong/wetext: {{e}}")

try:
    from modelscope.hub.snapshot_download import snapshot_download
    snapshot_download("iic/CosyVoice2-0.5B", cache_dir={json.dumps(str(cache_dir))})
    results.append("iic/CosyVoice2-0.5B")
except Exception as e:
    errors.append(f"iic/CosyVoice2-0.5B: {{e}}")

print(json.dumps({{"updated": results, "errors": errors}}))
"""
    try:
        result = subprocess.run(
            [python_exe, "-c", code],
            capture_output=True,
            text=True,
            timeout=600,
            cwd=str(COSYVOICE_DIR),
        )
        raw = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "{}"
        data = json.loads(raw)
        if result.returncode != 0 and not data.get("updated"):
            return {
                "status": "error",
                "message": f"模型更新失败: {result.stderr.strip()[:300]}",
                "updated": [],
                "errors": [result.stderr.strip()[:300]],
            }
        if data.get("errors"):
            return {
                "status": "partial",
                "message": f"部分更新成功: {', '.join(data['updated'])}；失败: {', '.join(data['errors'])}",
                "updated": data.get("updated", []),
                "errors": data.get("errors", []),
            }
        return {
            "status": "success",
            "message": f"模型已更新: {', '.join(data['updated'])}",
            "updated": data.get("updated", []),
            "errors": [],
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "模型更新超时（超过 10 分钟）", "updated": [], "errors": []}
    except Exception as exc:
        return {"status": "error", "message": str(exc), "updated": [], "errors": []}


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
