"""语音识别模块 (ASR)

基于 Whisper 实现语音转文字，支持本地模型和云端 API。

模型加载策略：
  - 使用全局单例 (_WHISPER_MODEL_CACHE)，首次调用时加载，后续复用
  - 默认模型：turbo（OpenAI 最新，速度接近 base，精度接近 medium）
"""

from pathlib import Path
from typing import Optional

from src.common.logger import get_logger
from src.common.config_manager import ConfigManager
from src.common.exceptions import ASRError

logger = get_logger(__name__)

# ── Whisper 全局模型缓存 ──
# key: model_size (如 "turbo")，value: 已加载的 whisper.Model 实例
_WHISPER_MODEL_CACHE: dict = {}


def _get_whisper_model(model_size: str):
    """获取（或首次加载）Whisper 模型单例

    第一次调用时下载/加载模型（turbo 约 809MB），后续调用直接复用，无需重复加载。
    """
    if model_size not in _WHISPER_MODEL_CACHE:
        try:
            import whisper
        except ImportError:
            raise ASRError("Whisper 未安装，请执行: uv add openai-whisper")
        logger.info(f"首次加载 Whisper 模型: {model_size}（后续调用将复用）")
        _WHISPER_MODEL_CACHE[model_size] = whisper.load_model(model_size)
        logger.info(f"Whisper {model_size} 模型加载完毕")
    return _WHISPER_MODEL_CACHE[model_size]


class ASREngine:
    """Whisper 语音识别引擎

    支持两种模式：
    - 本地模型：直接加载 Whisper 模型进行推理
    - 云端 API：对接远程 Whisper API 服务（适用于本地 GPU 不足场景）
    """

    def __init__(self, model_size: str = "turbo") -> None:
        """初始化 ASR 引擎

        Args:
            model_size: Whisper 模型大小 (tiny/base/small/medium/large)
        """
        self.config = ConfigManager()
        self.model_size = model_size
        # _model 不再持有实例引用，改用全局缓存 _WHISPER_MODEL_CACHE

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
            model = _get_whisper_model(self.model_size)
            result = model.transcribe(
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

        except ASRError:
            raise
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
            model = _get_whisper_model(self.model_size)
            result = model.transcribe(
                audio_path,
                language=language,
                fp16=False,
            )
            text = result["text"].strip()
            logger.info(f"本地转录完成，文本长度: {len(text)}")
            return text

        except ASRError:
            raise
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
        """从全局缓存中释放当前 model_size 的模型资源"""
        if self.model_size in _WHISPER_MODEL_CACHE:
            del _WHISPER_MODEL_CACHE[self.model_size]
            logger.info(f"Whisper {self.model_size} 模型已从缓存中释放")
