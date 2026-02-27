"""数字人驱动模块

支持 HeyGem 和 TuiliONNX 双引擎，通过 HTTP API 对接本地数字人服务。
"""

from pathlib import Path
from typing import Optional

import httpx

from src.common.logger import get_logger
from src.common.config_manager import ConfigManager
from src.common.exceptions import AvatarGenerateError
from src.common.file_utils import ensure_dir, generate_unique_filename

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "resources" / "models"


class HeyGemEngine:
    """HeyGem 数字人驱动引擎

    通过 HTTP API 对接 HeyGem 本地服务，实现音频驱动的口播数字人视频生成。
    """

    def __init__(self) -> None:
        self.config = ConfigManager()
        self.base_url = self.config.get_heygem_url()
        ensure_dir(MODELS_DIR)

    def list_models(self) -> list[dict]:
        """获取可用的数字人模型列表

        Returns:
            模型列表，每项包含 {"name": "模型名", "path": "模型路径"}
        """
        models = []
        if MODELS_DIR.exists():
            for d in sorted(MODELS_DIR.iterdir()):
                if d.is_dir():
                    models.append({"name": d.name, "path": str(d)})
        return models

    async def generate(
        self,
        model_name: str,
        audio_path: str,
        add_watermark: bool = True,
    ) -> dict:
        """生成数字人口播视频

        Args:
            model_name: 模型名称
            audio_path: 驱动音频文件路径
            add_watermark: 是否添加 AI 水印

        Returns:
            包含视频路径等信息的字典:
            {"video_path": str, "duration": float}

        Raises:
            AvatarGenerateError: 生成失败
        """
        if not Path(audio_path).exists():
            raise AvatarGenerateError(f"音频文件不存在: {audio_path}")

        models = self.list_models()
        model_names = [m["name"] for m in models]
        if model_name not in model_names:
            raise AvatarGenerateError(
                f"模型 '{model_name}' 不存在，可用模型: {model_names}"
            )

        try:
            output_dir = self.config.get_output_dir() / "avatar"
            ensure_dir(output_dir)

            async with httpx.AsyncClient(timeout=600.0) as client:
                with open(audio_path, "rb") as af:
                    files = {"audio": (Path(audio_path).name, af)}
                    data = {
                        "model_name": model_name,
                        "add_watermark": str(add_watermark).lower(),
                    }

                    response = await client.post(
                        f"{self.base_url}/api/generate",
                        files=files,
                        data=data,
                    )
                    response.raise_for_status()

                    # 保存视频
                    output_path = str(
                        output_dir / generate_unique_filename("mp4", "heygem")
                    )
                    with open(output_path, "wb") as f:
                        f.write(response.content)

                    logger.info(f"HeyGem 数字人视频生成完成: {output_path}")
                    return {"video_path": output_path}

        except httpx.RequestError as e:
            raise AvatarGenerateError(f"HeyGem 服务请求失败: {e}") from e
        except httpx.HTTPStatusError as e:
            raise AvatarGenerateError(
                f"HeyGem 服务返回错误 {e.response.status_code}: {e.response.text}"
            ) from e

    async def check_service(self) -> bool:
        """检查 HeyGem 服务是否可用"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False


class TuiliONNXEngine:
    """TuiliONNX 数字人驱动引擎

    通过 HTTP API 对接 TuiliONNX 服务，支持更多参数控制。
    """

    def __init__(self) -> None:
        self.config = ConfigManager()
        self.base_url = self.config.get_tuilionnx_url()

    def list_faces(self) -> list[dict]:
        """获取可用的人物模型列表

        Returns:
            人物列表
        """
        # 通过 API 从 TuiliONNX 服务获取
        try:
            import httpx as _httpx
            with _httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.base_url}/api/faces")
                response.raise_for_status()
                return response.json().get("faces", [])
        except Exception as e:
            logger.warning(f"获取人物模型列表失败: {e}")
            return []

    async def generate(
        self,
        face_id: str,
        audio_path: str,
        batch_size: int = 4,
        sync_offset: int = 0,
        scale_h: float = 1.6,
        scale_w: float = 3.6,
        compress_inference: bool = False,
        beautify_teeth: bool = False,
        add_watermark: bool = True,
    ) -> dict:
        """生成 TuiliONNX 数字人视频

        Args:
            face_id: 人物模型 ID
            audio_path: 驱动音频文件路径
            batch_size: 批次大小 (1-16)
            sync_offset: 音画同步偏移 (-10 到 10)
            scale_h: 遮罩高度比例
            scale_w: 遮罩宽度比例
            compress_inference: 是否压缩推理
            beautify_teeth: 是否美化牙齿
            add_watermark: 是否添加 AI 水印

        Returns:
            包含视频信息的字典:
            {"video_path": str, "duration": str, "download_url": str}

        Raises:
            AvatarGenerateError: 生成失败
        """
        if not Path(audio_path).exists():
            raise AvatarGenerateError(f"音频文件不存在: {audio_path}")

        try:
            output_dir = self.config.get_output_dir() / "avatar"
            ensure_dir(output_dir)

            async with httpx.AsyncClient(timeout=600.0) as client:
                with open(audio_path, "rb") as af:
                    files = {"audio": (Path(audio_path).name, af)}
                    data = {
                        "face_id": face_id,
                        "batch_size": str(batch_size),
                        "sync_offset": str(sync_offset),
                        "scale_h": str(scale_h),
                        "scale_w": str(scale_w),
                        "compress_inference": str(compress_inference).lower(),
                        "beautify_teeth": str(beautify_teeth).lower(),
                        "add_watermark": str(add_watermark).lower(),
                    }

                    response = await client.post(
                        f"{self.base_url}/api/generate",
                        files=files,
                        data=data,
                    )
                    response.raise_for_status()

                    result = response.json()

                    # 如果返回的是视频文件
                    if response.headers.get("content-type", "").startswith("video/"):
                        output_path = str(
                            output_dir / generate_unique_filename("mp4", "tuilionnx")
                        )
                        with open(output_path, "wb") as f:
                            f.write(response.content)
                        result["video_path"] = output_path

                    logger.info(f"TuiliONNX 数字人视频生成完成")
                    return result

        except httpx.RequestError as e:
            raise AvatarGenerateError(f"TuiliONNX 服务请求失败: {e}") from e
        except httpx.HTTPStatusError as e:
            raise AvatarGenerateError(
                f"TuiliONNX 服务返回错误 {e.response.status_code}: {e.response.text}"
            ) from e

    async def check_service(self) -> bool:
        """检查 TuiliONNX 服务是否可用"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False
