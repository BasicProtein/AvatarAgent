"""语音合成模块 (TTS)

基于 CosyVoice 实现语音合成和声音克隆。
通过 HTTP API 对接 CosyVoice 服务。
"""

import os
from pathlib import Path
from typing import Optional

import httpx

from src.common.logger import get_logger
from src.common.config_manager import ConfigManager
from src.common.exceptions import TTSError
from src.common.file_utils import ensure_dir, generate_unique_filename

logger = get_logger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
VOICES_DIR = PROJECT_ROOT / "resources" / "voices"


class TTSEngine:
    """CosyVoice 语音合成引擎

    通过 HTTP 请求对接 CosyVoice 服务，支持：
    - 音色列表管理
    - 基于预置音色的 TTS 合成
    - 基于参考音频的声音克隆
    - 语速调节
    """

    def __init__(self) -> None:
        self.config = ConfigManager()
        self.base_url = self.config.get_cosyvoice_url()
        ensure_dir(VOICES_DIR)

    def list_voices(self) -> list[dict]:
        """获取可用音色列表

        Returns:
            音色列表，每项包含 {"name": "音色名", "path": "文件路径"}
        """
        voices = []
        if VOICES_DIR.exists():
            for f in sorted(VOICES_DIR.iterdir()):
                if f.suffix.lower() in (".pt", ".pth", ".wav", ".mp3"):
                    voices.append({
                        "name": f.stem,
                        "path": str(f),
                    })
        return voices

    async def synthesize(
        self,
        text: str,
        voice_id: int = 0,
        speed: float = 1.0,
    ) -> str:
        """使用预置音色合成语音

        Args:
            text: 待合成文本
            voice_id: 音色索引
            speed: 语速倍率 (0.5-2.0)

        Returns:
            生成的音频文件路径

        Raises:
            TTSError: 合成失败
        """
        voices = self.list_voices()
        if not voices:
            raise TTSError("没有可用的音色文件，请在 resources/voices/ 目录放置音色文件")

        if voice_id < 0 or voice_id >= len(voices):
            raise TTSError(f"无效的音色索引: {voice_id}，可用范围: 0-{len(voices)-1}")

        voice = voices[voice_id]
        logger.info(f"使用音色 '{voice['name']}' 合成语音，语速: {speed}")

        try:
            output_dir = self.config.get_output_dir() / "audio"
            ensure_dir(output_dir)
            output_path = str(output_dir / generate_unique_filename("wav", "tts"))

            async with httpx.AsyncClient(timeout=120.0) as client:
                with open(voice["path"], "rb") as voice_file:
                    files = {"voice_file": (Path(voice["path"]).name, voice_file)}
                    data = {
                        "text": text,
                        "speed": str(speed),
                    }

                    response = await client.post(
                        f"{self.base_url}/api/tts",
                        files=files,
                        data=data,
                    )
                    response.raise_for_status()

                    # 保存音频文件
                    with open(output_path, "wb") as f:
                        f.write(response.content)

                    logger.info(f"语音合成完成: {output_path}")
                    return output_path

        except httpx.RequestError as e:
            raise TTSError(f"CosyVoice 服务请求失败: {e}") from e
        except httpx.HTTPStatusError as e:
            raise TTSError(
                f"CosyVoice 服务返回错误 {e.response.status_code}: {e.response.text}"
            ) from e

    async def clone_voice(
        self,
        reference_audio: str,
        text: str,
        speed: float = 1.0,
    ) -> str:
        """基于参考音频克隆声音并合成

        Args:
            reference_audio: 参考音频文件路径
            text: 待合成文本
            speed: 语速倍率

        Returns:
            生成的音频文件路径

        Raises:
            TTSError: 克隆/合成失败
        """
        if not Path(reference_audio).exists():
            raise TTSError(f"参考音频文件不存在: {reference_audio}")

        try:
            output_dir = self.config.get_output_dir() / "audio"
            ensure_dir(output_dir)
            output_path = str(output_dir / generate_unique_filename("wav", "clone"))

            async with httpx.AsyncClient(timeout=180.0) as client:
                with open(reference_audio, "rb") as ref_file:
                    files = {"reference_audio": (Path(reference_audio).name, ref_file)}
                    data = {
                        "text": text,
                        "speed": str(speed),
                    }

                    response = await client.post(
                        f"{self.base_url}/api/clone",
                        files=files,
                        data=data,
                    )
                    response.raise_for_status()

                    with open(output_path, "wb") as f:
                        f.write(response.content)

                    logger.info(f"声音克隆合成完成: {output_path}")
                    return output_path

        except httpx.RequestError as e:
            raise TTSError(f"声音克隆请求失败: {e}") from e

    async def check_service(self) -> bool:
        """检查 CosyVoice 服务是否可用

        Returns:
            服务是否在线
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False
