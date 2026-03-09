"""Text-to-speech integration for CosyVoice."""

from __future__ import annotations

import io
import re
import subprocess
import wave
from pathlib import Path

import httpx

from src.common.config_manager import ConfigManager
from src.common.exceptions import TTSError
from src.common.file_utils import ensure_dir, generate_unique_filename
from src.common.logger import get_logger

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
VOICES_DIR = PROJECT_ROOT / "resources" / "voices"

DEFAULT_SAMPLE_RATE = 22050
DEFAULT_CHUNK_CHARS = 80
DEFAULT_REQUEST_TIMEOUT = 120.0
DEFAULT_RETRIES = 2

SENTENCE_SPLIT_RE = re.compile(r"(?<=[\u3002\uff01\uff1f!?.;\n])")
PHRASE_SPLIT_RE = re.compile(r"(?<=[\uFF0C,\u3001\uFF1A:\s])")


def _is_wav(data: bytes) -> bool:
    return len(data) > 4 and data[:4] == b"RIFF"


def _pcm_to_wav(
    pcm_data: bytes,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    channels: int = 1,
    sample_width: int = 2,
) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)
    return buffer.getvalue()


def _ensure_wav_bytes(data: bytes, sample_rate: int) -> bytes:
    if _is_wav(data):
        return data
    return _pcm_to_wav(data, sample_rate=sample_rate)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


class TTSEngine:
    def __init__(self) -> None:
        self.config = ConfigManager()
        self.base_url = self.config.get_cosyvoice_url().rstrip("/")
        self.sample_rate = self.config.get_int(
            "cosyvoice",
            "sample_rate",
            DEFAULT_SAMPLE_RATE,
        )
        self.chunk_chars = self.config.get_int(
            "cosyvoice",
            "chunk_chars",
            DEFAULT_CHUNK_CHARS,
        )
        self.request_timeout = self.config.get_float(
            "cosyvoice",
            "request_timeout",
            DEFAULT_REQUEST_TIMEOUT,
        )
        ensure_dir(VOICES_DIR)

    def list_voices(self) -> list[dict]:
        voices: list[dict] = []
        if VOICES_DIR.exists():
            for file_path in sorted(VOICES_DIR.iterdir()):
                if file_path.suffix.lower() in {
                    ".pt",
                    ".pth",
                    ".wav",
                    ".mp3",
                    ".m4a",
                    ".ogg",
                    ".flac",
                    ".aac",
                    ".webm",
                }:
                    voices.append({"name": file_path.stem, "path": str(file_path)})
        return voices

    async def synthesize(
        self,
        text: str,
        voice_id: int = 0,
        speed: float = 1.0,
    ) -> str:
        voices = self.list_voices()
        if not voices:
            raise TTSError("No voice samples found under resources/voices.")

        if voice_id < 0 or voice_id >= len(voices):
            raise TTSError(f"Invalid voice_id: {voice_id}.")

        voice = voices[voice_id]
        logger.info(
            "Synthesizing speech with voice '%s', speed=%s",
            voice["name"],
            speed,
        )

        output_dir = self.config.get_output_dir() / "audio"
        ensure_dir(output_dir)
        output_path = str(output_dir / generate_unique_filename("wav", "tts"))

        audio_data = await self._synthesize_with_chunks(text, voice["path"])
        self._save_audio(audio_data, output_path)

        if abs(speed - 1.0) > 0.05:
            output_path = self._adjust_speed(output_path, speed)

        logger.info("Speech synthesis finished: %s", output_path)
        return output_path

    async def clone_voice(
        self,
        reference_audio: str,
        text: str,
        speed: float = 1.0,
    ) -> str:
        reference_path = Path(reference_audio)
        if not reference_path.exists():
            raise TTSError(f"Reference audio not found: {reference_audio}")

        output_dir = self.config.get_output_dir() / "audio"
        ensure_dir(output_dir)
        output_path = str(output_dir / generate_unique_filename("wav", "clone"))

        audio_data = await self._synthesize_with_chunks(text, str(reference_path))
        self._save_audio(audio_data, output_path)

        if abs(speed - 1.0) > 0.05:
            output_path = self._adjust_speed(output_path, speed)

        logger.info("Voice clone synthesis finished: %s", output_path)
        return output_path

    async def _synthesize_with_chunks(self, text: str, prompt_wav_path: str) -> bytes:
        chunks = self._chunk_text(text)
        if not chunks:
            raise TTSError("Text is empty. Nothing to synthesize.")

        wav_chunks: list[bytes] = []
        total = len(chunks)

        for index, chunk in enumerate(chunks, start=1):
            logger.info(
                "Submitting TTS chunk %s/%s (chars=%s)",
                index,
                total,
                len(chunk),
            )
            raw_audio = await self._inference_cross_lingual(chunk, prompt_wav_path)
            wav_chunks.append(_ensure_wav_bytes(raw_audio, self.sample_rate))

        if not wav_chunks:
            raise TTSError("CosyVoice returned no audio chunks.")

        return self._merge_wav_chunks(wav_chunks)

    def _chunk_text(self, text: str) -> list[str]:
        normalized = _normalize_text(text)
        if not normalized:
            return []

        max_chars = max(20, self.chunk_chars)
        sentence_parts = [
            part.strip()
            for part in SENTENCE_SPLIT_RE.split(normalized)
            if part.strip()
        ]
        if not sentence_parts:
            sentence_parts = [normalized]

        chunks: list[str] = []
        current = ""

        for sentence in sentence_parts:
            if len(sentence) > max_chars:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(self._split_long_sentence(sentence, max_chars))
                continue

            candidate = sentence if not current else f"{current} {sentence}"
            if len(candidate) <= max_chars:
                current = candidate
            else:
                chunks.append(current)
                current = sentence

        if current:
            chunks.append(current)

        return [chunk.strip() for chunk in chunks if chunk.strip()]

    def _split_long_sentence(self, sentence: str, max_chars: int) -> list[str]:
        phrase_parts = [
            part.strip()
            for part in PHRASE_SPLIT_RE.split(sentence)
            if part.strip()
        ]
        if len(phrase_parts) <= 1:
            return [
                sentence[index:index + max_chars].strip()
                for index in range(0, len(sentence), max_chars)
                if sentence[index:index + max_chars].strip()
            ]

        chunks: list[str] = []
        current = ""
        for part in phrase_parts:
            candidate = part if not current else f"{current} {part}"
            if len(candidate) <= max_chars:
                current = candidate
                continue

            if current:
                chunks.append(current)

            if len(part) <= max_chars:
                current = part
                continue

            chunks.extend(
                [
                    part[index:index + max_chars].strip()
                    for index in range(0, len(part), max_chars)
                    if part[index:index + max_chars].strip()
                ]
            )
            current = ""

        if current:
            chunks.append(current)
        return chunks

    async def _inference_cross_lingual(
        self,
        tts_text: str,
        prompt_wav_path: str,
    ) -> bytes:
        prompt_path = Path(prompt_wav_path)
        if not prompt_path.exists():
            raise TTSError(f"Voice sample not found: {prompt_wav_path}")

        timeout = httpx.Timeout(self.request_timeout, connect=5.0)
        last_error: Exception | None = None

        for attempt in range(1, DEFAULT_RETRIES + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=timeout,
                    follow_redirects=True,
                    trust_env=False,
                    transport=httpx.AsyncHTTPTransport(retries=0),
                ) as client:
                    with prompt_path.open("rb") as prompt_file:
                        response = await client.post(
                            f"{self.base_url}/inference_cross_lingual",
                            files={
                                "prompt_wav": (
                                    prompt_path.name,
                                    prompt_file,
                                    "audio/wav",
                                )
                            },
                            data={"tts_text": tts_text},
                        )

                response.raise_for_status()
                audio_data = response.content
                if not audio_data:
                    raise TTSError("CosyVoice returned an empty audio payload.")
                return audio_data
            except TTSError as exc:
                last_error = exc
                logger.warning(
                    "CosyVoice returned empty audio on attempt %s/%s for text length %s",
                    attempt,
                    DEFAULT_RETRIES,
                    len(tts_text),
                )
            except httpx.ConnectError as exc:
                raise TTSError(
                    f"Cannot reach CosyVoice service at {self.base_url}. "
                    "Please confirm the service is started."
                ) from exc
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text[:200]
                raise TTSError(
                    f"CosyVoice returned HTTP {exc.response.status_code}: {detail}"
                ) from exc
            except httpx.RequestError as exc:
                last_error = TTSError(f"CosyVoice request failed: {exc}")
                logger.warning(
                    "CosyVoice request failed on attempt %s/%s: %s",
                    attempt,
                    DEFAULT_RETRIES,
                    exc,
                )

        raise TTSError(str(last_error) if last_error else "CosyVoice request failed.")

    def _merge_wav_chunks(self, wav_chunks: list[bytes]) -> bytes:
        output = io.BytesIO()
        channels: int | None = None
        sample_width: int | None = None
        sample_rate: int | None = None

        with wave.open(output, "wb") as merged:
            for wav_chunk in wav_chunks:
                with wave.open(io.BytesIO(wav_chunk), "rb") as chunk:
                    if channels is None:
                        channels = chunk.getnchannels()
                        sample_width = chunk.getsampwidth()
                        sample_rate = chunk.getframerate()
                        merged.setnchannels(channels)
                        merged.setsampwidth(sample_width)
                        merged.setframerate(sample_rate)
                    merged.writeframes(chunk.readframes(chunk.getnframes()))

        return output.getvalue()

    def _save_audio(self, audio_data: bytes, output_path: str) -> None:
        wav_data = _ensure_wav_bytes(audio_data, self.sample_rate)
        with open(output_path, "wb") as output_file:
            output_file.write(wav_data)

    def _adjust_speed(self, audio_path: str, speed: float) -> str:
        adjusted_path = audio_path.replace(".wav", "_spd.wav")
        ffmpeg = self.config.get_ffmpeg_path()
        atempo = max(0.5, min(2.0, speed))

        try:
            result = subprocess.run(
                [
                    ffmpeg,
                    "-i",
                    audio_path,
                    "-filter:a",
                    f"atempo={atempo}",
                    "-acodec",
                    "pcm_s16le",
                    "-y",
                    adjusted_path,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                Path(audio_path).unlink(missing_ok=True)
                return adjusted_path
            logger.warning("ffmpeg speed adjust failed: %s", result.stderr[:200])
        except FileNotFoundError:
            logger.warning("ffmpeg not found, skipping speed adjustment.")
        except subprocess.TimeoutExpired:
            logger.warning("ffmpeg speed adjustment timed out.")
        except Exception as exc:
            logger.warning("Speed adjustment failed: %s", exc)

        return audio_path

    async def check_service(self) -> bool:
        try:
            async with httpx.AsyncClient(
                timeout=5.0,
                follow_redirects=True,
                trust_env=False,
                transport=httpx.AsyncHTTPTransport(retries=0),
            ) as client:
                response = await client.get(f"{self.base_url}/docs")
            return response.status_code == 200
        except Exception:
            return False
