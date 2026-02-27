"""语音识别模块 (ASR)

基于 Whisper 实现语音转文字，支持本地模型和云端 API。
"""

from pathlib import Path
from typing import Optional

from src.common.logger import get_logger
from src.common.config_manager import ConfigManager
from src.common.exceptions import ASRError

logger = get_logger(__name__)


class ASREngine:
    """Whisper 语音识别引擎

    支持两种模式：
    - 本地模型：直接加载 Whisper 模型进行推理
    - 云端 API：对接远程 Whisper API 服务（适用于本地 GPU 不足场景）
    """

    def __init__(self, model_size: str = "medium") -> None:
        """初始化 ASR 引擎

        Args:
            model_size: Whisper 模型大小 (tiny/base/small/medium/large)
        """
        self.config = ConfigManager()
        self.model_size = model_size
        self._model = None

    async def transcribe(
        self,
        audio_path: str,
        language: str = "zh",
    ) -> str:
        """语音转文字

        Args:
            audio_path: 音频文件路径
            language: 语言代码，默认中文

        Returns:
            转录的文本

        Raises:
            ASRError: 转录失败
        """
        if not Path(audio_path).exists():
            raise ASRError(f"音频文件不存在: {audio_path}")

        # 优先使用云端 GPU
        if self.config.is_cloud_gpu_enabled():
            return await self._transcribe_remote(audio_path, language)

        return await self._transcribe_local(audio_path, language)

    async def transcribe_with_timestamps(
        self,
        audio_path: str,
        language: str = "zh",
    ) -> list[dict]:
        """带时间戳的语音转文字（用于字幕生成）

        Args:
            audio_path: 音频文件路径
            language: 语言代码

        Returns:
            带时间戳的文本段列表，格式:
            [{"start": 0.0, "end": 2.5, "text": "你好"}, ...]

        Raises:
            ASRError: 转录失败
        """
        if not Path(audio_path).exists():
            raise ASRError(f"音频文件不存在: {audio_path}")

        if self.config.is_cloud_gpu_enabled():
            return await self._transcribe_remote_with_timestamps(audio_path, language)

        return await self._transcribe_local_with_timestamps(audio_path, language)

    async def _transcribe_local_with_timestamps(
        self, audio_path: str, language: str
    ) -> list[dict]:
        """本地 Whisper 模型带时间戳转录"""
        try:
            if self._model is None:
                import whisper
                logger.info(f"加载 Whisper 模型: {self.model_size}")
                self._model = whisper.load_model(self.model_size)

            result = self._model.transcribe(
                audio_path,
                language=language,
                fp16=False,
            )

            segments = []
            for seg in result.get("segments", []):
                segments.append({
                    "start": round(seg["start"], 3),
                    "end": round(seg["end"], 3),
                    "text": seg["text"].strip(),
                })

            logger.info(f"本地带时间戳转录完成，共 {len(segments)} 段")
            return segments

        except ImportError:
            raise ASRError("Whisper 未安装，请执行: pip install openai-whisper")
        except Exception as e:
            raise ASRError(f"本地带时间戳转录失败: {e}") from e

    async def _transcribe_remote_with_timestamps(
        self, audio_path: str, language: str
    ) -> list[dict]:
        """云端 API 带时间戳转录"""
        import httpx

        cloud_config = self.config.get_cloud_gpu_config()
        api_url = cloud_config["api_url"]
        api_key = cloud_config["api_key"]

        if not api_url:
            raise ASRError("云端 GPU API 地址未配置")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                with open(audio_path, "rb") as f:
                    files = {"file": (Path(audio_path).name, f, "audio/wav")}
                    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
                    response = await client.post(
                        f"{api_url}/asr/transcribe",
                        files=files,
                        data={
                            "language": language,
                            "model": self.model_size,
                            "timestamps": "true",
                        },
                        headers=headers,
                    )
                    response.raise_for_status()

                    data = response.json()
                    segments = data.get("segments", [])
                    logger.info(f"云端带时间戳转录完成，共 {len(segments)} 段")
                    return segments

        except httpx.RequestError as e:
            raise ASRError(f"云端带时间戳转录请求失败: {e}") from e

    async def _transcribe_local(self, audio_path: str, language: str) -> str:
        """本地 Whisper 模型转录

        Args:
            audio_path: 音频文件路径
            language: 语言代码

        Returns:
            转录文本
        """
        try:
            if self._model is None:
                import whisper
                logger.info(f"加载 Whisper 模型: {self.model_size}")
                self._model = whisper.load_model(self.model_size)

            result = self._model.transcribe(
                audio_path,
                language=language,
                fp16=False,
            )
            text = result["text"].strip()
            logger.info(f"本地转录完成，文本长度: {len(text)}")
            return text

        except ImportError:
            raise ASRError("Whisper 未安装，请执行: pip install openai-whisper")
        except Exception as e:
            raise ASRError(f"本地转录失败: {e}") from e

    async def _transcribe_remote(self, audio_path: str, language: str) -> str:
        """云端 API 转录

        Args:
            audio_path: 音频文件路径
            language: 语言代码

        Returns:
            转录文本
        """
        import httpx

        cloud_config = self.config.get_cloud_gpu_config()
        api_url = cloud_config["api_url"]
        api_key = cloud_config["api_key"]

        if not api_url:
            raise ASRError("云端 GPU API 地址未配置")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                with open(audio_path, "rb") as f:
                    files = {"file": (Path(audio_path).name, f, "audio/wav")}
                    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
                    response = await client.post(
                        f"{api_url}/asr/transcribe",
                        files=files,
                        data={"language": language, "model": self.model_size},
                        headers=headers,
                    )
                    response.raise_for_status()

                    data = response.json()
                    text = data.get("text", "")
                    logger.info(f"云端转录完成，文本长度: {len(text)}")
                    return text

        except httpx.RequestError as e:
            raise ASRError(f"云端转录请求失败: {e}") from e

    def unload_model(self) -> None:
        """释放模型资源"""
        if self._model is not None:
            del self._model
            self._model = None
            logger.info("Whisper 模型已释放")
