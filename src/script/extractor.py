"""对标视频文案提取模块

从视频链接下载视频/音频，通过 ASR 识别转为文字。
支持抖音等平台的短链接解析。
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from src.common.logger import get_logger
from src.common.config_manager import ConfigManager
from src.common.exceptions import ScriptExtractError
from src.common.file_utils import ensure_dir, generate_unique_filename

logger = get_logger(__name__)


class ScriptExtractor:
    """对标视频文案提取器

    工作流程：
    1. 解析视频链接（支持短链接跳转）
    2. 使用 yt-dlp 下载视频/提取音频
    3. 使用 Whisper ASR 转录为文本
    """

    def __init__(self) -> None:
        self.config = ConfigManager()
        self._temp_dir = Path(tempfile.mkdtemp(prefix="avatar_extract_"))

    def extract_from_url(self, video_url: str) -> str:
        """从视频链接提取口播文案

        Args:
            video_url: 视频链接（支持抖音/快手等短链接）

        Returns:
            提取的文案文本

        Raises:
            ScriptExtractError: 提取失败
        """
        try:
            logger.info(f"开始提取视频文案: {video_url}")

            # Step 1: 下载音频
            audio_path = self._download_audio(video_url)
            logger.info(f"音频下载完成: {audio_path}")

            # Step 2: ASR 转录
            text = self._transcribe(audio_path)
            logger.info(f"文案提取完成，长度: {len(text)} 字符")

            return text

        except Exception as e:
            raise ScriptExtractError(f"文案提取失败: {e}") from e

    def extract_from_audio(self, audio_path: str) -> str:
        """从音频文件提取文案

        Args:
            audio_path: 音频文件路径

        Returns:
            提取的文案文本

        Raises:
            ScriptExtractError: 提取失败
        """
        if not Path(audio_path).exists():
            raise ScriptExtractError(f"音频文件不存在: {audio_path}")

        try:
            return self._transcribe(audio_path)
        except Exception as e:
            raise ScriptExtractError(f"音频转录失败: {e}") from e

    def _download_audio(self, url: str) -> str:
        """使用 yt-dlp 从视频链接下载音频

        Args:
            url: 视频链接

        Returns:
            下载的音频文件路径
        """
        output_path = str(self._temp_dir / generate_unique_filename("wav", "audio"))

        cmd = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "wav",
            "--audio-quality", "0",
            "-o", output_path,
            url,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                raise ScriptExtractError(f"yt-dlp 下载失败: {result.stderr}")

            # yt-dlp 可能修改扩展名，查找实际文件
            possible_path = Path(output_path)
            if possible_path.exists():
                return str(possible_path)

            # 查找同名但不同扩展名的文件
            for f in self._temp_dir.iterdir():
                if f.stem == possible_path.stem:
                    return str(f)

            raise ScriptExtractError("下载完成但未找到音频文件")

        except subprocess.TimeoutExpired:
            raise ScriptExtractError("视频下载超时")

    def _transcribe(self, audio_path: str) -> str:
        """使用 Whisper 进行语音转录

        Args:
            audio_path: 音频文件路径

        Returns:
            转录文本
        """
        import asyncio
        from src.audio.asr import ASREngine

        asr = ASREngine()
        try:
            # 尝试获取当前事件循环
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # 如果已在异步环境中，创建新线程运行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(
                    asyncio.run, asr.transcribe(audio_path)
                ).result()
            return result
        else:
            return asyncio.run(asr.transcribe(audio_path))

    def cleanup(self) -> None:
        """清理临时文件"""
        import shutil
        if self._temp_dir.exists():
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            logger.info("已清理提取器临时文件")
