"""对标视频文案提取模块

从视频链接下载视频/音频，通过 ASR 识别转为文字。

音频获取策略（三层降级）：
  1. 抖音/TikTok → douyin-tiktok-scraper 本地库（自动生成签名参数，无需 Cookie）
  2. 层 1 失败 → api.douyin.wtf 公共 HTTP API（带 3 次重试，15s 超时/次）
  3. 其他平台 / 前两层均失败 → yt-dlp CLI（支持 B 站、YouTube 等）
"""

import asyncio
import contextlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple

import httpx

from src.common.logger import get_logger
from src.common.config_manager import ConfigManager
from src.common.exceptions import ScriptExtractError
from src.common.file_utils import ensure_dir, generate_unique_filename

logger = get_logger(__name__)

# ── api.douyin.wtf 公共 API（层 2 备用）──
_DOUYIN_API_BASE = "https://api.douyin.wtf/api"
_API_TIMEOUT = 20.0       # 单次请求超时（秒）
_API_RETRIES = 3          # 最多重试次数
_API_RETRY_DELAY = 2.0    # 重试间隔（秒）

_DOWNLOAD_TIMEOUT = 120.0  # 视频文件流式下载超时（秒）

# 代理相关环境变量（访问抖音等国内站点时需要临时禁用）
_PROXY_ENV_KEYS = [
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy",
]

# 抖音 / TikTok 链接特征（含短链）
_DOUYIN_PATTERNS = [
    r"douyin\.com",
    r"v\.douyin\.com",
    r"tiktok\.com",
    r"vm\.tiktok\.com",
]


def _is_douyin_url(url: str) -> bool:
    """判断是否为抖音 / TikTok 链接"""
    return any(re.search(p, url, re.IGNORECASE) for p in _DOUYIN_PATTERNS)


@contextlib.contextmanager
def _no_proxy():
    """临时禁用代理环境变量（访问国内站点时避免代理干扰）"""
    saved = {}
    for key in _PROXY_ENV_KEYS:
        if key in os.environ:
            saved[key] = os.environ.pop(key)
    try:
        yield
    finally:
        os.environ.update(saved)


class ScriptExtractor:
    """对标视频文案提取器

    工作流程：
    1. 判断链接平台
    2a. 抖音/TikTok → api.douyin.wtf 解析无水印直链 → httpx 直接下载（无需 Cookie）
    2b. 其他平台 / API 失败  → yt-dlp 回退下载
    3. Whisper ASR 转录为中文文本
    """

    def __init__(self) -> None:
        self.config = ConfigManager()
        self._temp_dir = Path(tempfile.mkdtemp(prefix="avatar_extract_"))
        self._douyin_share_html_cache: dict[str, str] = {}
        self._text_fallback: Optional[str] = None

    # ──────────────────────────────── 公开方法 ────────────────────────────────

    def extract_from_url(self, video_url: str) -> str:
        """从视频链接提取口播文案

        Args:
            video_url: 视频链接（支持抖音短链/长链/TikTok/B站等）

        Returns:
            提取的文案文本

        Raises:
            ScriptExtractError: 提取失败
        """
        try:
            logger.info(f"开始提取视频文案: {video_url}")
            self._text_fallback = self._prepare_text_fallback(video_url)

            audio_path = self._download_audio(video_url)
            logger.info(f"音频下载完成: {audio_path}")

            text = self._transcribe(audio_path)
            logger.info(f"文案提取完成，长度: {len(text)} 字符")
            return text

        except ScriptExtractError:
            if self._text_fallback:
                logger.warning("音频转文案失败，回退使用分享页文案")
                return self._text_fallback
            raise
        except Exception as e:
            if self._text_fallback:
                logger.warning(f"音频转文案异常，回退使用分享页文案: {e}")
                return self._text_fallback
            raise ScriptExtractError(f"文案提取失败: {e}") from e

    def extract_from_audio(self, audio_path: str) -> str:
        """从本地音频文件提取文案

        Args:
            audio_path: 音频文件路径

        Returns:
            提取的文案文本
        """
        if not Path(audio_path).exists():
            raise ScriptExtractError(f"音频文件不存在: {audio_path}")
        try:
            return self._transcribe(audio_path)
        except Exception as e:
            raise ScriptExtractError(f"音频转录失败: {e}") from e

    def cleanup(self) -> None:
        """清理临时文件"""
        if self._temp_dir.exists():
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            logger.info("已清理提取器临时文件")

    def _prepare_text_fallback(self, url: str) -> Optional[str]:
        """为可直接读取文案的平台准备兜底文本。"""
        if not _is_douyin_url(url):
            return None
        try:
            return self._extract_desc_from_share_item(self._get_douyin_share_item(url))
        except Exception as e:
            logger.warning(f"分享页文案兜底准备失败: {e}")
            return None

    # ──────────────────────────── 私有：音频下载 ─────────────────────────────

    def _download_audio(self, url: str) -> str:
        """下载音频，四层降级策略

        Returns:
            本地音频文件绝对路径
        """
        if _is_douyin_url(url):
            # 国内站点禁用代理，避免代理干扰
            with _no_proxy():
                # 层 0：直接解析 iesdouyin 分享页内嵌数据（轻量、无 Cookie）
                try:
                    return self._download_via_douyin_share_page(url)
                except Exception as e:
                    logger.warning(f"[层0] 分享页解析失败: {e}")

                # 层 1：Playwright 浏览器渲染（抓取视频流地址）
                try:
                    return self._download_via_playwright(url)
                except Exception as e:
                    logger.warning(f"[层1] Playwright 失败: {e}")

                # 层 2：douyin-tiktok-scraper 本地库
                try:
                    return self._download_via_scraper_lib(url)
                except Exception as e:
                    logger.warning(f"[层2] douyin-tiktok-scraper 失败: {e}")

                # 层 3：api.douyin.wtf 公共 API（带重试）
                try:
                    return self._download_via_douyin_api(url)
                except Exception as e:
                    logger.warning(f"[层3] api.douyin.wtf 失败: {e}，回退到 yt-dlp")

                # 层 4：yt-dlp（兜底，支持所有平台）
                return self._download_via_ytdlp(url)

        # 非抖音平台，直接 yt-dlp
        return self._download_via_ytdlp(url)

    def _download_via_douyin_share_page(self, url: str) -> str:
        """直接解析抖音分享页 HTML 中的 videoInfoRes 并下载视频。

        该链路不依赖 Playwright、第三方解析库或 yt-dlp cookie。
        """
        item = self._get_douyin_share_item(url)
        video_id = item.get("aweme_id") or self._extract_douyin_video_id(url) or "unknown"
        video_direct_url = self._pick_video_url((item.get("video") or {}))
        logger.info(f"[层0] 分享页解析成功，video_id={video_id}")

        raw_path = self._temp_dir / generate_unique_filename("mp4", "raw")
        self._stream_download(video_direct_url, raw_path)

        wav_path = self._temp_dir / generate_unique_filename("wav", "audio")
        if self._ffmpeg_extract_audio(str(raw_path), str(wav_path)):
            raw_path.unlink(missing_ok=True)
            return str(wav_path)
        return str(raw_path)

    def _extract_url_from_share_html(self, html: str) -> str:
        """从抖音分享页 HTML 中提取视频直链。"""
        item = self._extract_share_item_from_html(html)
        direct_url = self._pick_video_url((item.get("video") or {}))
        if not direct_url:
            raise ScriptExtractError("分享页数据中未找到可用视频地址")
        return direct_url

    def _get_douyin_share_item(self, url: str) -> dict:
        """获取抖音分享页中的单条视频数据。"""
        video_id = self._extract_douyin_video_id(url)
        if not video_id:
            raise ScriptExtractError("无法从链接中提取抖音视频 ID")

        html = self._fetch_douyin_share_html(video_id)
        return self._extract_share_item_from_html(html)

    def _fetch_douyin_share_html(self, video_id: str) -> str:
        """拉取抖音移动端分享页 HTML，并做进程内缓存。"""
        cached = self._douyin_share_html_cache.get(video_id)
        if cached:
            return cached

        share_url = f"https://www.iesdouyin.com/share/video/{video_id}/"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/16.6 Mobile/15E148 Safari/604.1"
            ),
            "Referer": "https://www.douyin.com/",
        }

        with httpx.Client(
            timeout=_API_TIMEOUT,
            follow_redirects=True,
            trust_env=False,
        ) as client:
            resp = client.get(share_url, headers=headers)
            resp.raise_for_status()
            html = resp.text

        self._douyin_share_html_cache[video_id] = html
        return html

    def _extract_share_item_from_html(self, html: str) -> dict:
        """从抖音分享页 HTML 中提取 item_list[0]。"""
        video_info = self._extract_embedded_json_object(html, '"videoInfoRes":')
        item_list = video_info.get("item_list") or []
        if not item_list:
            raise ScriptExtractError("分享页数据中未找到 item_list")

        return item_list[0] or {}

    def _extract_desc_from_share_item(self, item: dict) -> Optional[str]:
        """从分享页视频数据中提取可作为兜底的文案。"""
        desc = (item.get("desc") or "").strip()
        return desc or None

    def _extract_embedded_json_object(self, text: str, marker: str) -> dict:
        """从 HTML/JS 文本中按 marker 提取后续 JSON 对象。"""
        marker_index = text.find(marker)
        if marker_index == -1:
            raise ScriptExtractError(f"页面中未找到标记: {marker}")

        start = text.find("{", marker_index + len(marker))
        if start == -1:
            raise ScriptExtractError(f"标记后未找到 JSON 对象: {marker}")

        depth = 0
        in_string = False
        escape = False

        for index in range(start, len(text)):
            ch = text[index]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue

            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:index + 1])
                    except json.JSONDecodeError as e:
                        raise ScriptExtractError(f"分享页 JSON 解析失败: {e}") from e

        raise ScriptExtractError("分享页 JSON 对象不完整")

    def _pick_video_url(self, video_data: dict) -> Optional[str]:
        """从抖音视频数据中挑选一个可下载的视频地址。"""
        addr_candidates = [
            video_data.get("play_addr"),
            video_data.get("play_api"),
            video_data.get("download_addr"),
        ]

        bit_rates = video_data.get("bit_rate") or []
        for bit_rate in bit_rates:
            addr_candidates.extend([
                bit_rate.get("play_addr"),
                bit_rate.get("play_api"),
                bit_rate.get("download_addr"),
            ])

        for addr in addr_candidates:
            if not isinstance(addr, dict):
                continue
            url_list = addr.get("url_list") or []
            for candidate in url_list:
                if isinstance(candidate, str) and candidate.startswith("http"):
                    return candidate.replace("\\u002F", "/")

        return None

    # ──────────────── 层 0：Playwright 浏览器渲染（最可靠）─────────────────

    def _download_via_playwright(self, url: str) -> str:
        """通过 Playwright 浏览器加载抖音分享页，捕获视频流地址并下载

        使用移动端分享页（iesdouyin.com），自动点击播放按钮触发视频加载，
        通过网络拦截获取真实视频 URL。

        Returns:
            本地音频/视频文件路径
        """
        video_id = self._extract_douyin_video_id(url)
        if not video_id:
            raise ScriptExtractError("无法从链接中提取抖音视频 ID")

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(self._run_playwright_sync, video_id).result()
        else:
            return self._run_playwright_sync(video_id)

    def _extract_douyin_video_id(self, url: str) -> Optional[str]:
        """从抖音链接中提取视频 ID（支持短链和长链）"""
        # 长链：https://www.douyin.com/video/7614160296634027306
        match = re.search(r"video/(\d+)", url)
        if match:
            return match.group(1)

        # 短链需要先解析重定向获取真实 URL
        try:
            with httpx.Client(follow_redirects=True, timeout=15, trust_env=False) as client:
                resp = client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X)"
                })
                match = re.search(r"video/(\d+)", str(resp.url))
                if match:
                    return match.group(1)
        except Exception as e:
            logger.warning(f"解析抖音短链失败: {e}")

        return None

    def _run_playwright_sync(self, video_id: str) -> str:
        """在新事件循环中运行 Playwright 抓取视频"""

        async def _inner():
            from playwright.async_api import async_playwright

            video_urls: list[str] = []
            share_url = f"https://www.iesdouyin.com/share/video/{video_id}/"

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
                        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                        "Version/16.6 Mobile/15E148 Safari/604.1"
                    ),
                    viewport={"width": 375, "height": 812},
                    is_mobile=True,
                )
                page = await context.new_page()

                async def on_response(response):
                    ct = response.headers.get("content-type", "")
                    if "video" in ct:
                        video_urls.append(response.url)

                page.on("response", on_response)

                await page.goto(share_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)

                # 点击播放按钮触发视频加载
                play_btn = await page.query_selector(
                    ".play-btn, [class*=play], .video-container"
                )
                if play_btn:
                    await play_btn.click()
                else:
                    await page.click("body", position={"x": 187, "y": 300})
                await page.wait_for_timeout(5000)

                # 如果网络拦截没有捕获，尝试从 video 元素获取
                if not video_urls:
                    src = await page.evaluate("""() => {
                        const v = document.querySelector('video');
                        return v ? (v.src || v.currentSrc) : null;
                    }""")
                    if src and src.startswith("http"):
                        video_urls.append(src)

                await browser.close()

            if not video_urls:
                raise ScriptExtractError("Playwright 未能捕获到视频流地址")
            return video_urls[0]

        video_url = asyncio.run(_inner())
        logger.info(f"[层0] Playwright 获取视频 URL 成功")

        # 下载视频并提取音频
        raw_path = self._temp_dir / generate_unique_filename("mp4", "raw")
        self._stream_download(video_url, raw_path)
        logger.info(f"[层0] 视频下载完成 ({raw_path.stat().st_size // 1024} KB)")

        wav_path = self._temp_dir / generate_unique_filename("wav", "audio")
        if self._ffmpeg_extract_audio(str(raw_path), str(wav_path)):
            raw_path.unlink(missing_ok=True)
            return str(wav_path)
        return str(raw_path)

    # ─────────────────── 层 1：douyin-tiktok-scraper 本地库 ──────────────────

    def _download_via_scraper_lib(self, url: str) -> str:
        """使用 douyin-tiktok-scraper Python 库本地解析，无需外网 API 调用

        该库在本地自动生成 msToken / X-Bogus / A-Bogus 等签名参数，
        直接请求抖音官方接口，无需 Cookie，无需代理。

        Returns:
            本地音频/视频文件路径
        """
        from douyin_tiktok_scraper.scraper import Scraper

        # 在独立事件循环中运行异步库
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(self._run_scraper_sync, url).result()
        else:
            result = self._run_scraper_sync(url)

        return result

    def _run_scraper_sync(self, url: str) -> str:
        """在新事件循环中同步运行 scraper（供 ThreadPoolExecutor 调用）"""
        import asyncio
        from douyin_tiktok_scraper.scraper import Scraper

        async def _inner():
            api = Scraper()
            data = await api.hybrid_parsing(url)
            return data

        data = asyncio.run(_inner())

        # 解析视频直链
        video_direct_url = self._extract_url_from_scraper_data(data)
        logger.info(f"[层1] scraper 解析成功，准备下载视频")

        raw_path = self._temp_dir / generate_unique_filename("mp4", "raw")
        self._stream_download(video_direct_url, raw_path)

        wav_path = self._temp_dir / generate_unique_filename("wav", "audio")
        if self._ffmpeg_extract_audio(str(raw_path), str(wav_path)):
            raw_path.unlink(missing_ok=True)
            return str(wav_path)
        return str(raw_path)

    def _extract_url_from_scraper_data(self, data: dict) -> str:
        """从 scraper 返回数据中提取无水印视频直链"""
        # douyin-tiktok-scraper 返回结构与 api.douyin.wtf 基本一致
        video_info: dict = data.get("video") or {}
        addr_block: dict = (
            video_info.get("play_addr")
            or video_info.get("download_addr")
            or {}
        )
        url_list: list = addr_block.get("url_list", [])

        if not url_list:
            # 部分版本结构不同，尝试 bit_rate 列表
            bit_rates = video_info.get("bit_rate") or []
            for br in bit_rates:
                ul = (br.get("play_addr") or {}).get("url_list", [])
                if ul:
                    url_list = ul
                    break

        if not url_list:
            raise ScriptExtractError(
                "scraper 返回数据中未找到视频直链（视频可能已删除）"
            )
        return url_list[0]

    # ─────────────── 层 2：api.douyin.wtf 公共 HTTP API（带重试）────────────

    def _download_via_douyin_api(self, url: str) -> str:
        """通过 api.douyin.wtf 解析无水印直链并下载（带重试机制）

        Returns:
            本地音频/视频文件路径
        """
        video_url, title = self._resolve_douyin_url_with_retry(url)
        logger.info(f"[层2] API 解析成功: {title}")

        raw_path = self._temp_dir / generate_unique_filename("mp4", "raw")
        self._stream_download(video_url, raw_path)
        logger.info(f"[层2] 视频下载完成 ({raw_path.stat().st_size // 1024} KB)")

        wav_path = self._temp_dir / generate_unique_filename("wav", "audio")
        if self._ffmpeg_extract_audio(str(raw_path), str(wav_path)):
            raw_path.unlink(missing_ok=True)
            return str(wav_path)

        logger.warning("[层2] ffmpeg 不可用，直接用视频文件进行 ASR")
        return str(raw_path)

    def _resolve_douyin_url_with_retry(self, url: str) -> Tuple[str, str]:
        """调用 api.douyin.wtf，最多重试 _API_RETRIES 次"""
        api_endpoint = f"{_DOUYIN_API_BASE}/hybrid/video_data"
        last_err: Exception = RuntimeError("未知错误")

        for attempt in range(1, _API_RETRIES + 1):
            try:
                with httpx.Client(
                    timeout=_API_TIMEOUT,
                    follow_redirects=True,
                    trust_env=False,
                ) as client:
                    resp = client.get(api_endpoint, params={"url": url, "minimal": "false"})
                    resp.raise_for_status()
                    data = resp.json()

                video_info: dict = data.get("video") or {}
                addr_block: dict = (
                    video_info.get("play_addr")
                    or video_info.get("download_addr")
                    or {}
                )
                url_list: list = addr_block.get("url_list", [])

                if not url_list:
                    raise ScriptExtractError("API 返回数据中未找到视频直链")

                title = data.get("desc") or data.get("title") or "unknown"
                return url_list[0], title

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_err = e
                logger.warning(
                    f"[层2] 第 {attempt}/{_API_RETRIES} 次请求超时/连接失败: {e}，"
                    f"{'重试中...' if attempt < _API_RETRIES else '放弃'}"
                )
                if attempt < _API_RETRIES:
                    time.sleep(_API_RETRY_DELAY)
            except httpx.HTTPStatusError as e:
                raise ScriptExtractError(
                    f"api.douyin.wtf 返回 HTTP {e.response.status_code}"
                ) from e

        raise ScriptExtractError(f"api.douyin.wtf 多次请求均失败: {last_err}")



    def _stream_download(self, url: str, dest: Path) -> None:
        """流式下载文件，防止大文件一次性加载到内存"""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.douyin.com/",
        }
        try:
            with httpx.Client(
                timeout=_DOWNLOAD_TIMEOUT,
                follow_redirects=True,
                trust_env=False,
            ) as client:
                with client.stream("GET", url, headers=headers) as resp:
                    resp.raise_for_status()
                    with open(dest, "wb") as f:
                        for chunk in resp.iter_bytes(chunk_size=8192):
                            f.write(chunk)
        except httpx.TimeoutException:
            raise ScriptExtractError(f"视频文件下载超时（{_DOWNLOAD_TIMEOUT}s）")
        except Exception as e:
            raise ScriptExtractError(f"视频文件下载失败: {e}")

    def _ffmpeg_extract_audio(self, input_path: str, output_wav: str) -> bool:
        """用 ffmpeg 将视频/音频转为 16kHz 单声道 WAV（Whisper 最佳格式）

        Returns:
            True 表示成功，False 表示 ffmpeg 不可用或转换失败
        """
        try:
            ffmpeg_bin = self.config.get_ffmpeg_path()
        except Exception:
            ffmpeg_bin = "ffmpeg"

        try:
            result = subprocess.run(
                [
                    ffmpeg_bin, "-y",
                    "-i", input_path,
                    "-vn",                    # 去掉视频流
                    "-acodec", "pcm_s16le",   # 16-bit PCM WAV
                    "-ar", "16000",           # 16kHz（Whisper 原生采样率）
                    "-ac", "1",               # 单声道，减少文件大小
                    output_wav,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                logger.info("ffmpeg 音频提取成功 (16kHz mono wav)")
                return True
            logger.warning(f"ffmpeg 返回非零退出码: {result.stderr[:200]}")
            return False
        except FileNotFoundError:
            logger.warning("系统中未找到 ffmpeg，跳过音频提取步骤")
            return False
        except subprocess.TimeoutExpired:
            logger.warning("ffmpeg 超时（60s）")
            return False

    def _download_via_ytdlp(self, url: str) -> str:
        """方案 B（回退）：使用 yt-dlp CLI 下载音频（支持 B 站等非抖音平台）

        Returns:
            本地音频文件路径

        Raises:
            ScriptExtractError: 下载失败
        """
        output_path = str(self._temp_dir / generate_unique_filename("wav", "audio"))

        cmd = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "wav",
            "--audio-quality", "0",
            "--no-playlist",
            "-o", output_path,
            url,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,
            )
            if result.returncode != 0:
                raise ScriptExtractError(f"yt-dlp 下载失败: {result.stderr[:300]}")

            # yt-dlp 可能自动修改扩展名（如 wav → m4a），搜索实际文件
            possible_path = Path(output_path)
            if possible_path.exists():
                return str(possible_path)

            for f in self._temp_dir.iterdir():
                if f.stem == possible_path.stem:
                    return str(f)

            raise ScriptExtractError("yt-dlp 下载完成但未找到音频文件")

        except subprocess.TimeoutExpired:
            raise ScriptExtractError("yt-dlp 下载超时（超过 180 秒）")

    # ──────────────────────────── 私有：ASR 转录 ─────────────────────────────

    def _transcribe(self, audio_path: str) -> str:
        """使用 Whisper 进行语音转录

        兼容同步和异步调用环境（FastAPI 路由内 / 独立脚本均可）
        """
        import asyncio
        from src.audio.asr import ASREngine

        # Whisper 的 load_audio() 需要通过 subprocess 调用 ffmpeg，
        # 确保 ffmpeg 所在目录在 PATH 中
        try:
            ffmpeg_bin = self.config.get_ffmpeg_path()
            ffmpeg_dir = str(Path(ffmpeg_bin).parent)
            if ffmpeg_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
                logger.info(f"已将 ffmpeg 目录添加到 PATH: {ffmpeg_dir}")
        except Exception:
            pass

        asr = ASREngine()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # 已在异步事件循环内（FastAPI），在独立线程中运行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, asr.transcribe(audio_path)).result()
        else:
            return asyncio.run(asr.transcribe(audio_path))
