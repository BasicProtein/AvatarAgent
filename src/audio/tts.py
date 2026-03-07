"""语音合成模块 (TTS)

基于 CosyVoice 实现语音合成和声音克隆。
通过 HTTP API 对接 CosyVoice 官方 FastAPI 服务。

支持的 CosyVoice API 端点：
- /inference_cross_lingual  跨语言声音克隆（仅需参考音频）
- /inference_zero_shot      零样本声音克隆（需参考音频 + prompt 文本）
- /inference_sft            预置音色合成

官方仓库: https://github.com/FunAudioLLM/CosyVoice
"""

import io
import subprocess
import wave
from pathlib import Path

import httpx

from src.common.logger import get_logger
from src.common.config_manager import ConfigManager
from src.common.exceptions import TTSError
from src.common.file_utils import ensure_dir, generate_unique_filename

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
VOICES_DIR = PROJECT_ROOT / "resources" / "voices"

DEFAULT_SAMPLE_RATE = 22050


def _is_wav(data: bytes) -> bool:
    """检查数据是否已经是 WAV 格式（以 RIFF 头开头）"""
    return len(data) > 4 and data[:4] == b"RIFF"


def _pcm_to_wav(
    pcm_data: bytes,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    channels: int = 1,
    sample_width: int = 2,
) -> bytes:
    """将原始 PCM int16 数据封装为 WAV 格式

    CosyVoice 官方 API 通过 StreamingResponse 返回原始 int16 PCM 字节流，
    需要添加 WAV 头才能被播放器和 ffmpeg 正确识别。
    """
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


class TTSEngine:
    """CosyVoice 语音合成引擎

    通过 HTTP 请求对接 CosyVoice 官方 FastAPI 服务，支持：
    - 音色列表管理（本地 resources/voices/ 目录）
    - 基于参考音频的跨语言声音克隆（inference_cross_lingual）
    - 基于参考音频 + prompt 文本的零样本克隆（inference_zero_shot）
    - 语速调节（通过 ffmpeg atempo 滤镜后处理）
    """

    def __init__(self) -> None:
        self.config = ConfigManager()
        self.base_url = self.config.get_cosyvoice_url()
        self.sample_rate = self.config.get_int(
            "cosyvoice", "sample_rate", DEFAULT_SAMPLE_RATE
        )
        ensure_dir(VOICES_DIR)

    def list_voices(self) -> list[dict]:
        """获取可用音色列表

        Returns:
            音色列表，每项包含 {"name": "音色名", "path": "文件路径"}
        """
        voices = []
        if VOICES_DIR.exists():
            for f in sorted(VOICES_DIR.iterdir()):
                if f.suffix.lower() in (
                    ".pt", ".pth", ".wav", ".mp3", ".m4a",
                    ".ogg", ".flac", ".aac", ".webm",
                ):
                    voices.append({"name": f.stem, "path": str(f)})
        return voices

    # ──────────────────────── 合成接口 ────────────────────────

    async def synthesize(
        self,
        text: str,
        voice_id: int = 0,
        speed: float = 1.0,
    ) -> str:
        """使用预置音色合成语音

        将 resources/voices/ 中选定的音色文件作为参考音频，
        调用 CosyVoice inference_cross_lingual 实现声音克隆合成。

        Args:
            text: 待合成文本
            voice_id: 音色索引（对应 list_voices 的顺序）
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

        output_dir = self.config.get_output_dir() / "audio"
        ensure_dir(output_dir)
        output_path = str(output_dir / generate_unique_filename("wav", "tts"))

        audio_data = await self._inference_cross_lingual(text, voice["path"])
        self._save_audio(audio_data, output_path)

        if abs(speed - 1.0) > 0.05:
            output_path = self._adjust_speed(output_path, speed)

        logger.info(f"语音合成完成: {output_path}")
        return output_path

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

        output_dir = self.config.get_output_dir() / "audio"
        ensure_dir(output_dir)
        output_path = str(output_dir / generate_unique_filename("wav", "clone"))

        audio_data = await self._inference_cross_lingual(text, reference_audio)
        self._save_audio(audio_data, output_path)

        if abs(speed - 1.0) > 0.05:
            output_path = self._adjust_speed(output_path, speed)

        logger.info(f"声音克隆合成完成: {output_path}")
        return output_path

    # ──────────────────────── CosyVoice API 调用 ────────────────────────

    async def _inference_cross_lingual(
        self, tts_text: str, prompt_wav_path: str
    ) -> bytes:
        """调用 CosyVoice /inference_cross_lingual 接口

        跨语言声音克隆：仅需参考音频即可克隆音色并合成目标文本，
        无需提供参考音频对应的 prompt 文本。

        官方 API 签名:
            POST /inference_cross_lingual
            Form: tts_text (str), prompt_wav (UploadFile)
            Response: StreamingResponse (raw int16 PCM bytes)

        Args:
            tts_text: 待合成文本
            prompt_wav_path: 参考音频文件路径

        Returns:
            音频数据字节（可能是 WAV 或原始 PCM，取决于 CosyVoice 部署方式）
        """
        try:
            async with httpx.AsyncClient(
                    timeout=180.0,
                    transport=httpx.AsyncHTTPTransport(),
                ) as client:
                with open(prompt_wav_path, "rb") as f:
                    files = {
                        "prompt_wav": (Path(prompt_wav_path).name, f, "audio/wav"),
                    }
                    data = {"tts_text": tts_text}

                    response = await client.post(
                        f"{self.base_url}/inference_cross_lingual",
                        files=files,
                        data=data,
                    )
                    response.raise_for_status()

                    if len(response.content) == 0:
                        raise TTSError("CosyVoice 返回了空音频数据")

                    return response.content

        except httpx.ConnectError:
            raise TTSError(
                f"无法连接 CosyVoice 服务 ({self.base_url})，"
                "请确认服务已启动。可在「设置」页查看服务状态。"
            )
        except httpx.RequestError as e:
            raise TTSError(f"CosyVoice 服务请求失败: {e}") from e
        except httpx.HTTPStatusError as e:
            raise TTSError(
                f"CosyVoice 服务返回错误 {e.response.status_code}: "
                f"{e.response.text[:200]}"
            ) from e

    # ──────────────────────── 音频保存与后处理 ────────────────────────

    def _save_audio(self, audio_data: bytes, output_path: str) -> None:
        """保存音频数据到文件

        自动检测数据格式：如果已是 WAV（部分第三方 CosyVoice 封装会直接返回 WAV），
        则原样保存；否则当作原始 PCM int16 数据，封装为 WAV 格式。
        """
        if _is_wav(audio_data):
            with open(output_path, "wb") as f:
                f.write(audio_data)
        else:
            wav_data = _pcm_to_wav(audio_data, self.sample_rate)
            with open(output_path, "wb") as f:
                f.write(wav_data)

    def _adjust_speed(self, audio_path: str, speed: float) -> str:
        """通过 ffmpeg atempo 滤镜调节音频语速

        CosyVoice 官方 API 不支持语速参数，因此通过后处理实现。
        atempo 滤镜接受 0.5-100.0 范围，此处限制为 0.5-2.0。

        Args:
            audio_path: 输入音频路径
            speed: 语速倍率 (0.5-2.0)

        Returns:
            处理后的音频路径（失败时返回原路径）
        """
        adjusted_path = audio_path.replace(".wav", "_spd.wav")
        ffmpeg = self.config.get_ffmpeg_path()
        atempo = max(0.5, min(2.0, speed))

        try:
            result = subprocess.run(
                [
                    ffmpeg, "-i", audio_path,
                    "-filter:a", f"atempo={atempo}",
                    "-acodec", "pcm_s16le",
                    "-y", adjusted_path,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                Path(audio_path).unlink(missing_ok=True)
                return adjusted_path
            logger.warning(f"ffmpeg 调速失败: {result.stderr[:200]}")
        except FileNotFoundError:
            logger.warning("ffmpeg 未找到，跳过语速调节")
        except subprocess.TimeoutExpired:
            logger.warning("ffmpeg 调速超时")
        except Exception as e:
            logger.warning(f"语速调节异常: {e}")

        return audio_path

    # ──────────────────────── 服务健康检查 ────────────────────────

    async def check_service(self) -> bool:
        """检查 CosyVoice 服务是否可用

        CosyVoice 官方 FastAPI 服务没有专门的 /health 端点，
        通过访问 FastAPI 自动生成的 /docs 页面来判断服务是否在线。

        Returns:
            服务是否在线
        """
        try:
            async with httpx.AsyncClient(
                timeout=5.0,
                follow_redirects=True,
                transport=httpx.AsyncHTTPTransport(),
            ) as client:
                response = await client.get(f"{self.base_url}/docs")
                return response.status_code == 200
        except Exception:
            return False
