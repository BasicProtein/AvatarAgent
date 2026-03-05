"""
Whisper 模型断点续传下载器 v3
- 使用 requests 流式 + Range 断点续传
- 连接断开自动重试（Azure CDN 会频繁断连，需要多次续传）
- SHA256 校验确保文件完整
"""

import hashlib
import sys
import time
from pathlib import Path

# ── 获取模型信息 ──────────────────────────────────────────────────────────────
try:
    import whisper
    MODEL_URL = whisper._MODELS.get("turbo") or whisper._MODELS.get("large-v3-turbo")
    if not MODEL_URL:
        raise KeyError("turbo model not found")
except Exception as e:
    print(f"[错误] 无法从 whisper 获取模型地址: {e}")
    sys.exit(1)

MODEL_SHA256 = MODEL_URL.split("/models/")[1].split("/")[0]
CACHE_DIR    = Path.home() / ".cache" / "whisper"
SAVE_PATH    = CACHE_DIR / "large-v3-turbo.pt"
TMP_PATH     = SAVE_PATH.with_suffix(".pt.tmp")

GREEN  = "\033[92m"; YELLOW = "\033[93m"; RED = "\033[91m"
CYAN   = "\033[96m"; BOLD   = "\033[1m";  RESET  = "\033[0m"

def ok(msg):   print(f"\n  {GREEN}✅ {msg}{RESET}")
def warn(msg): print(f"\n  {YELLOW}⚠️  {msg}{RESET}")
def err(msg):  print(f"\n  {RED}❌ {msg}{RESET}")
def info(msg): print(f"  {CYAN}ℹ  {msg}{RESET}")
def sep():     print(f"\n{'─'*56}")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_segment(total_size: int, max_retries: int = 999) -> None:
    """循环续传，直到下载完成"""
    import requests

    CHUNK = 512 * 1024   # 512KB 写一次磁盘
    retry = 0

    while True:
        resume_pos = TMP_PATH.stat().st_size if TMP_PATH.exists() else 0

        # 已经下完了？
        if total_size > 0 and resume_pos >= total_size:
            ok(f"文件已完整（{resume_pos / 1024 / 1024:.1f} MB）")
            break

        pct = resume_pos / total_size * 100 if total_size else 0
        if retry > 0:
            warn(f"连接中断，自动续传（已下载 {pct:.1f}%，第 {retry} 次重连）...")
            time.sleep(min(retry * 2, 10))  # 指数退避，最多等 10s

        headers = {}
        if resume_pos > 0:
            headers["Range"] = f"bytes={resume_pos}-"

        try:
            resp = requests.get(MODEL_URL, headers=headers, stream=True, timeout=30)

            if resp.status_code == 416:
                # 服务器说 Range 超出，说明文件已经完了
                ok("文件已完整下载")
                break

            resp.raise_for_status()

            t_last  = time.time()
            speed_b = 0

            with open(TMP_PATH, "ab" if resume_pos > 0 else "wb") as f:
                for chunk in resp.iter_content(chunk_size=CHUNK):
                    if not chunk:
                        continue
                    f.write(chunk)
                    resume_pos += len(chunk)
                    speed_b    += len(chunk)

                    now = time.time()
                    if now - t_last >= 1.0:
                        speed_mb = speed_b / (now - t_last) / 1024 / 1024
                        pct_now  = resume_pos / total_size * 100 if total_size else 0
                        bar_len  = 34
                        filled   = int(bar_len * resume_pos / total_size) if total_size else 0
                        bar      = "█" * filled + "░" * (bar_len - filled)
                        remain   = total_size - resume_pos
                        eta_s    = int(remain / (speed_mb * 1024 * 1024)) if speed_mb > 0.01 else 0
                        eta      = f"{eta_s//60}m{eta_s%60:02d}s"
                        print(
                            f"\r  [{bar}] {pct_now:5.1f}%  "
                            f"{resume_pos/1024/1024:.0f}/{total_size/1024/1024:.0f}MB  "
                            f"{speed_mb:.1f}MB/s  ETA:{eta}   ",
                            end="", flush=True
                        )
                        t_last  = now
                        speed_b = 0

            # 正常读完才到这里
            ok(f"本段下载完成")
            break

        except Exception as e:
            retry += 1
            if retry > max_retries:
                raise RuntimeError(f"超过最大重试次数 ({max_retries})，最后错误: {e}")
            # 继续循环，续传


def get_total_size() -> int:
    import requests
    resp = requests.head(MODEL_URL, timeout=15, allow_redirects=True)
    return int(resp.headers.get("Content-Length", 0))


# ── 主流程 ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sep()
    print(f"{BOLD}  Whisper turbo 模型下载器 v3（自动断点续传）{RESET}")
    sep()
    info(f"URL:  {MODEL_URL[:60]}...")
    info(f"保存: {SAVE_PATH}")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # 处理旧的完整文件（可能损坏）
    if SAVE_PATH.exists():
        size_mb = SAVE_PATH.stat().st_size / 1024 / 1024
        info(f"检测到已有文件（{size_mb:.0f} MB），直接校验...")
        if file_sha256(SAVE_PATH) == MODEL_SHA256:
            ok("SHA256 校验通过，无需重新下载 ✅")
            print(f"\n  双击运行 {BOLD}2_test_device.bat{RESET} 进行测试。\n")
            sys.exit(0)
        else:
            warn("文件已损坏，删除并重新下载")
            SAVE_PATH.unlink()

    # 获取总大小
    sep()
    info("获取文件总大小...")
    try:
        total_size = get_total_size()
        info(f"文件大小: {total_size / 1024 / 1024:.1f} MB")
    except Exception as e:
        warn(f"无法获取大小 ({e})，将以未知大小下载")
        total_size = 0

    # 已有 tmp 文件
    if TMP_PATH.exists():
        already = TMP_PATH.stat().st_size / 1024 / 1024
        info(f"发现断点文件，已下载 {already:.1f} MB，继续...")

    print()
    print(f"{BOLD}开始下载（遇到断连自动续传，请勿关闭窗口）...{RESET}")
    print()

    try:
        download_segment(total_size)
    except Exception as e:
        err(f"下载失败: {e}")
        sys.exit(1)

    # 将 tmp 重命名为正式文件
    if TMP_PATH.exists():
        TMP_PATH.rename(SAVE_PATH)

    # SHA256 校验
    sep()
    print(f"{BOLD}验证 SHA256...{RESET}")
    info("正在校验（约 15 秒）...")
    if file_sha256(SAVE_PATH) == MODEL_SHA256:
        ok("SHA256 校验通过 ✅")
    else:
        err("文件损坏！已删除，请重新运行本脚本")
        SAVE_PATH.unlink(missing_ok=True)
        sys.exit(1)

    sep()
    print(f"\n{BOLD}{GREEN}🎉 模型就绪！{RESET}")
    print(f"  双击运行 {BOLD}2_test_device.bat{RESET} 进行 RTX 3050 GPU 测试。\n")
