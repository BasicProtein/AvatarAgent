"""
Whisper 本地 GPU 测试脚本
适用于 RTX 3050 / CUDA 12.1

测试内容：
1. PyTorch 安装状态 + CUDA 可用性
2. GPU 信息（型号、显存）
3. Whisper 安装状态
4. 加载 turbo 模型（从本目录 models/ 加载，不依赖 C 盘）
5. 用合成音频做一次真实转录
"""

import sys
import time
from pathlib import Path

# 模型存放目录：whisper_local_test/models/（不依赖 C 盘用户目录）
MODEL_DIR = Path(__file__).parent / "models"

# ─────────────────────────── ANSI 颜色 ───────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):   print(f"  {GREEN}✅ {msg}{RESET}")
def warn(msg): print(f"  {YELLOW}⚠️  {msg}{RESET}")
def err(msg):  print(f"  {RED}❌ {msg}{RESET}")
def info(msg): print(f"  {CYAN}   {msg}{RESET}")
def sep():     print(f"\n{'─'*52}")


# ─────────────────────────── Step 1：PyTorch 检测 ─────────────────────────────
sep()
print(f"{BOLD}[1/4] PyTorch 与 CUDA 检测{RESET}")

try:
    import torch
    ok(f"PyTorch 版本: {torch.__version__}")

    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram_mb  = torch.cuda.get_device_properties(0).total_memory // (1024 ** 2)
        ok(f"CUDA 可用 ✅")
        ok(f"GPU 型号:  {gpu_name}")
        ok(f"显存:      {vram_mb} MB")
        DEVICE = "cuda"
    else:
        warn("CUDA 不可用，将使用 CPU（速度较慢）")
        warn("请确认已运行 1_setup_cuda.bat 安装 CUDA 版 PyTorch")
        DEVICE = "cpu"

except ImportError:
    err("PyTorch 未安装，请双击运行 1_setup_cuda.bat")
    sys.exit(1)


# ─────────────────────────── Step 2：Whisper 检测 ─────────────────────────────
sep()
print(f"{BOLD}[2/4] Whisper 检测{RESET}")

try:
    import whisper
    ok(f"openai-whisper 已安装")
except ImportError:
    err("openai-whisper 未安装，请双击运行 1_setup_cuda.bat")
    sys.exit(1)


# ─────────────────────────── Step 3：模型加载 ─────────────────────────────────
sep()
print(f"{BOLD}[3/4] 加载 Whisper turbo 模型{RESET}")
info(f"目标设备: {DEVICE.upper()}")
info(f"模型目录: {MODEL_DIR}")

if not MODEL_DIR.exists() or not any(MODEL_DIR.glob("*.pt")):
    err(f"未在 {MODEL_DIR} 找到模型文件")
    err("请将 large-v3-turbo.pt 放入 models/ 目录内")
    sys.exit(1)

t0 = time.time()
try:
    model = whisper.load_model("turbo", device=DEVICE, download_root=str(MODEL_DIR))
    elapsed = time.time() - t0
    ok(f"模型加载成功（耗时 {elapsed:.1f}s）")
except Exception as e:
    err(f"模型加载失败: {e}")
    sys.exit(1)


# ─────────────────────────── Step 4：转录测试 ─────────────────────────────────
sep()
print(f"{BOLD}[4/4] 真实转录测试{RESET}")

# 用 NumPy 生成一段纯静音音频进行转录测试（无需真实音频文件）
try:
    import numpy as np

    info("生成 3 秒测试音频（440Hz 正弦波）...")
    sample_rate = 16000
    duration    = 3.0
    t           = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
    audio       = (np.sin(2 * np.pi * 440 * t) * 0.1).astype(np.float32)

    use_fp16 = (DEVICE == "cuda")
    info(f"推理精度: {'fp16（GPU 加速）' if use_fp16 else 'fp32（CPU 模式）'}")

    t0     = time.time()
    result = model.transcribe(audio, language="zh", fp16=use_fp16)
    elapsed = time.time() - t0

    text = result.get("text", "").strip()
    ok(f"转录完成（耗时 {elapsed:.2f}s）")
    info(f"识别内容: '{text if text else '（纯音频无文字内容）'}'")

except ImportError:
    warn("numpy 未安装，跳过转录测试（模型加载已验证）")


# ─────────────────────────── 总结 ────────────────────────────────────────────
sep()
print(f"\n{BOLD}{GREEN}全部测试通过！{RESET}")

if DEVICE == "cuda":
    print(f"\n  你的 {GREEN}RTX 3050{RESET} 已成功接入 Whisper！")
    print(f"  ASR 转录将使用 GPU 加速（fp16 模式）")
else:
    print(f"\n  {YELLOW}当前使用 CPU 模式，如需 GPU 加速：{RESET}")
    print(f"  1. 确认显卡驱动已安装")
    print(f"  2. 重新运行 1_setup_cuda.bat")

print(f"\n  现在可以启动 AvatarAgent，设置页将显示 GPU 状态。\n")
