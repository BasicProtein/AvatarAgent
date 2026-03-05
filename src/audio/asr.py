"""语音识别模块 (ASR)

基于 Whisper 实现语音转文字，支持三种运行模式：

  模式 A — 本地 GPU（推荐，终端用户默认）：
    安装 openai-whisper 后自动运行，有 CUDA/MPS 则自动 GPU 加速。
    模型大小可通过 config.ini [whisper] model_size 配置。

  模式 B — 本地 CPU（GPU 不可用时自动降级）：
    自动检测到无 GPU 时以 fp32 精度在 CPU 上运行，速度较慢。

  模式 C — 云端 GPU（AutoDL 等，config.ini [cloud_gpu] enabled=true）：
    将音频发送到远程 Whisper API 服务处理，本地无需安装 torch/whisper。

模型加载策略：
  - 全局单例缓存 (_WHISPER_MODEL_CACHE)，首次调用时加载，后续复用
  - 默认模型：turbo（OpenAI 最新，速度快且精度高，约 809MB）
"""

from pathlib import Path
from typing import Optional

from src.common.logger import get_logger
from src.common.config_manager import ConfigManager
from src.common.exceptions import ASRError

logger = get_logger(__name__)

# ── Whisper 全局模型缓存 ──
# key: (model_size, device)，value: 已加载的 whisper.Model 实例
_WHISPER_MODEL_CACHE: dict = {}


def _detect_device() -> str:
    """自动检测最优推理设备

    优先级：CUDA GPU > Apple Silicon MPS > CPU

    Returns:
        设备字符串：'cuda' / 'mps' / 'cpu'
    """
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"检测到 CUDA GPU: {gpu_name}，将使用 GPU 加速")
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            logger.info("检测到 Apple Silicon MPS，将使用 MPS 加速")
            return "mps"
    except ImportError:
        pass
    logger.info("未检测到 GPU，将使用 CPU 运行 Whisper（速度较慢）")
    return "cpu"


def get_local_asr_status() -> dict:
    """获取本地 ASR 环境状态（供 API 或前端展示）

    Returns:
        包含 whisper_installed、torch_installed、device、gpu_name 的字典
    """
    status = {
        "whisper_installed": False,
        "torch_installed": False,
        "device": "cpu",
        "gpu_name": None,
        "cuda_available": False,
    }
    try:
        import whisper  # noqa: F401
        status["whisper_installed"] = True
    except ImportError:
        pass

    try:
        import torch
        status["torch_installed"] = True
        status["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            status["device"] = "cuda"
            status["gpu_name"] = torch.cuda.get_device_name(0)
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            status["device"] = "mps"
            status["gpu_name"] = "Apple Silicon GPU"
        else:
            status["device"] = "cpu"
    except ImportError:
        pass

    return status


def _get_whisper_model(model_size: str, device: str):
    """获取（或首次加载）Whisper 模型单例

    第一次调用时加载模型，后续调用直接复用。
    同一 model_size + device 组合共享同一实例。
    模型位置从 ConfigManager 读取，默认存入项目内 models/whisper 目录。
    """
    cache_key = (model_size, device)
    if cache_key not in _WHISPER_MODEL_CACHE:
        try:
            import whisper
        except ImportError:
            raise ASRError(
                "Whisper 未安装。请执行: uv add openai-whisper\n"
                "（首次安装会自动下载 torch CPU 版本，如需 GPU 加速请参考安装指南）"
            )
        # 读取自定义模型目录（由 ConfigManager 提供，没有则用 whisper 默认的 ~/.cache/whisper）
        _cfg = ConfigManager()
        model_dir = _cfg.get("whisper", "model_dir", "")
        download_root = model_dir if model_dir else None

        logger.info(f"首次加载 Whisper {model_size} 模型到 {device}"
                    f"（目录: {download_root or '默认'}）")
        _WHISPER_MODEL_CACHE[cache_key] = whisper.load_model(
            model_size, device=device, download_root=download_root
        )
        logger.info(f"Whisper {model_size} 模型加载完毕（设备: {device}）")
    return _WHISPER_MODEL_CACHE[cache_key]


class ASREngine:
    """Whisper 语音识别引擎

    支持三种模式（按优先级自动切换）：
    - 模式 A：本地 GPU（有 CUDA/MPS 时自动使用）
    - 模式 B：本地 CPU（无 GPU 时自动降级）
    - 模式 C：云端 API（config.ini [cloud_gpu] enabled=true 时使用）
    """

    def __init__(self, model_size: Optional[str] = None) -> None:
        """初始化 ASR 引擎

        Args:
            model_size: Whisper 模型大小（tiny/base/small/medium/large/turbo）。
                        为 None 时从 config.ini [whisper] model_size 读取，
                        默认为 'turbo'。
        """
        self.config = ConfigManager()
        # 模型大小：参数 > config.ini > 默认值
        self.model_size = (
            model_size
            or self.config.get("whisper", "model_size", "turbo")
        )
        # 设备检测延迟到首次使用（避免启动时因 torch 未安装报错）
        self._device: Optional[str] = None

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
            if self._device is None:
                self._device = _detect_device()
            use_fp16 = self._device in ("cuda", "mps")

            model = _get_whisper_model(self.model_size, self._device)
            result = model.transcribe(
                audio_path,
                language=language,
                fp16=use_fp16,
            )

            segments = []
            for seg in result.get("segments", []):
                segments.append({
                    "start": round(seg["start"], 3),
                    "end": round(seg["end"], 3),
                    "text": seg["text"].strip(),
                })

            logger.info(
                f"本地带时间戳转录完成，设备: {self._device}，共 {len(segments)} 段"
            )
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
                        f"{api_url}/asr/transcribe/timestamps",
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
            if self._device is None:
                self._device = _detect_device()
            use_fp16 = self._device in ("cuda", "mps")  # CPU 不支持 fp16

            model = _get_whisper_model(self.model_size, self._device)
            result = model.transcribe(
                audio_path,
                language=language,
                fp16=use_fp16,
            )
            text = result["text"].strip()
            logger.info(
                f"本地转录完成，设备: {self._device}，"
                f"fp16: {use_fp16}，文本长度: {len(text)}"
            )
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
