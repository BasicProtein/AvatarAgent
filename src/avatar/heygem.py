"""数字人驱动模块

支持 HeyGem 和 TuiliONNX 双引擎，通过 HTTP API 对接本地数字人服务。

HeyGem 真实 API（端口 8383）：
  POST /easy/submit  — 提交任务（JSON body 含本地文件路径 + UUID）
  GET  /easy/query?code=<uuid> — 轮询任务状态
"""

import asyncio
import uuid
from pathlib import Path
from typing import Callable, Optional

import httpx

from src.common.logger import get_logger
from src.common.config_manager import ConfigManager
from src.common.exceptions import AvatarGenerateError
from src.common.file_utils import ensure_dir, generate_unique_filename

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "resources" / "models"

# HeyGem 生成轮询参数
_POLL_INTERVAL = 3.0   # 秒
_POLL_TIMEOUT = 600.0  # 秒


class HeyGemEngine:
    """HeyGem 数字人驱动引擎

    通过 HTTP API 对接 HeyGem 本地服务（端口 8383），
    实现音频驱动的口播数字人视频生成。
    """

    def __init__(self) -> None:
        self.config = ConfigManager()
        self.base_url = self.config.get_heygem_url()
        self._path_mapping = self.config.get_heygem_path_mapping()
        ensure_dir(MODELS_DIR)

    def _to_container_path(self, host_path: str, kind: str) -> str:
        """将宿主机绝对路径转换为 Docker 容器内路径。

        Args:
            host_path: 宿主机文件绝对路径
            kind: "audio" 或 "video"

        Returns:
            容器内路径（若未配置映射则原样返回）
        """
        host_dir = self._path_mapping.get(f"{kind}_host_dir", "").rstrip("/\\")
        container_dir = self._path_mapping.get(f"{kind}_container_dir", "").rstrip("/")

        if not host_dir or not container_dir:
            return host_path

        # 规范化宿主机路径以便比较（统一用正斜杠）
        normalized = host_path.replace("\\", "/")
        host_dir_normalized = host_dir.replace("\\", "/")

        if normalized.lower().startswith(host_dir_normalized.lower()):
            relative = normalized[len(host_dir_normalized):].lstrip("/")
            return f"{container_dir}/{relative}"

        return host_path

    def list_models(self) -> list[dict]:
        """获取可用的数字人模型列表（扫描 resources/models/ 目录）

        Returns:
            模型列表，每项包含 {"name": "模型名", "path": "模型路径", "video_path": "视频文件路径"}
        """
        models = []
        if MODELS_DIR.exists():
            for d in sorted(MODELS_DIR.iterdir()):
                if d.is_dir() and d.name != "__pycache__":
                    # 找到目录中第一个视频文件
                    video_path = ""
                    for ext in (".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm"):
                        found = list(d.glob(f"*{ext}"))
                        if found:
                            video_path = str(found[0])
                            break
                    models.append({
                        "name": d.name,
                        "path": str(d),
                        "video_path": video_path,
                    })
        return models

    def _find_model_video(self, model_name: str) -> str:
        """根据模型名查找对应的视频文件路径"""
        models = self.list_models()
        for m in models:
            if m["name"] == model_name:
                if not m["video_path"]:
                    raise AvatarGenerateError(
                        f"模型 '{model_name}' 目录中未找到视频文件"
                    )
                return m["video_path"]
        model_names = [m["name"] for m in models]
        raise AvatarGenerateError(
            f"模型 '{model_name}' 不存在，可用模型: {model_names}"
        )

    async def generate(
        self,
        model_name: str,
        audio_path: str,
        add_watermark: bool = False,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> dict:
        """生成数字人口播视频

        使用 HeyGem 真实 API：
        1. POST /easy/submit  提交任务
        2. GET  /easy/query?code=<uuid>  轮询直到完成

        Args:
            model_name: 模型名称（对应 resources/models/ 下的子目录）
            audio_path: 驱动音频文件路径（服务端绝对路径）
            add_watermark: 是否添加水印（0=关闭，1=开启）
            on_progress: 进度回调，接收进度文本

        Returns:
            {"video_path": str}

        Raises:
            AvatarGenerateError: 生成失败
        """
        if not Path(audio_path).exists():
            raise AvatarGenerateError(f"音频文件不存在: {audio_path}")

        video_path = self._find_model_video(model_name)
        task_code = str(uuid.uuid4())

        def _log(msg: str) -> None:
            logger.info(msg)
            if on_progress:
                on_progress(msg)

        # 将宿主机路径转换为 Docker 容器内路径
        container_audio = self._to_container_path(audio_path, "audio")
        container_video = self._to_container_path(video_path, "video")
        _log(f"[HeyGem] 提交任务 code={task_code}, 模型={model_name}")
        if container_audio != audio_path:
            _log(f"[HeyGem] 音频路径映射: {audio_path} → {container_audio}")
        if container_video != video_path:
            _log(f"[HeyGem] 视频路径映射: {video_path} → {container_video}")

        payload = {
            "audio_url": container_audio,
            "video_url": container_video,
            "code": task_code,
            "chaofen": 0,
            "watermark_switch": 1 if add_watermark else 0,
            "pn": 1,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0, transport=httpx.AsyncHTTPTransport()) as client:
                resp = await client.post(
                    f"{self.base_url}/easy/submit",
                    json=payload,
                )
                resp.raise_for_status()
                submit_data = resp.json()
                _log(f"[HeyGem] 任务已提交: {submit_data}")

        except httpx.RequestError as e:
            raise AvatarGenerateError(f"HeyGem 服务请求失败: {e}") from e
        except httpx.HTTPStatusError as e:
            raise AvatarGenerateError(
                f"HeyGem 服务返回错误 {e.response.status_code}: {e.response.text}"
            ) from e

        # 轮询任务状态
        elapsed = 0.0
        output_video_path = ""
        async with httpx.AsyncClient(timeout=15.0, transport=httpx.AsyncHTTPTransport()) as client:
            while elapsed < _POLL_TIMEOUT:
                await asyncio.sleep(_POLL_INTERVAL)
                elapsed += _POLL_INTERVAL

                try:
                    query_resp = await client.get(
                        f"{self.base_url}/easy/query",
                        params={"code": task_code},
                    )
                    query_resp.raise_for_status()
                    data = query_resp.json()
                except Exception as e:
                    _log(f"[HeyGem] 轮询异常: {e}，继续等待...")
                    continue

                # HeyGem 返回格式参考: {"data": {"status": 2, "video_url": "..."}}
                inner = data.get("data") or data
                status = inner.get("status", -1)
                _log(f"[HeyGem] 轮询 {elapsed:.0f}s, status={status}")

                if status == 2:  # 成功
                    # HeyGem 返回字段为 "result"（非 "video_url"）
                    output_video_path = inner.get("result", "") or inner.get("video_url", "") or inner.get("result_url", "")
                    break
                elif status in (3, 4):  # 明确失败
                    err_msg = inner.get("msg") or inner.get("message") or "未知错误"
                    raise AvatarGenerateError(f"HeyGem 任务失败 (status={status}): {err_msg}")
                # status=0/1/-1 均视为处理中，继续轮询

        if not output_video_path:
            raise AvatarGenerateError("HeyGem 生成超时或未返回视频路径")

        # 将容器内路径 /code/data/temp/xxx.mp4 转换为宿主机路径
        # 容器的 /code/data/temp 已挂载到 output/avatar/
        container_temp = "/code/data/temp"
        avatar_host_dir = str(self.config.get_output_dir() / "avatar")
        if output_video_path.startswith(container_temp):
            filename = output_video_path[len(container_temp):].lstrip("/")
            output_video_path = str(Path(avatar_host_dir) / filename)
            _log(f"[HeyGem] 结果路径映射: {inner.get('result','')} → {output_video_path}")

        _log(f"[HeyGem] 视频生成完成: {output_video_path}")
        return {"video_path": output_video_path}

    async def check_service(self) -> bool:
        """检查 HeyGem 服务是否可用"""
        try:
            async with httpx.AsyncClient(timeout=5.0, transport=httpx.AsyncHTTPTransport()) as client:
                # HeyGem 无专用 health 端点，用 query 探测服务连通性
                response = await client.get(
                    f"{self.base_url}/easy/query",
                    params={"code": "ping"},
                )
                # 4xx/5xx 说明服务在线但拒绝了请求，也算 online
                return True
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
            with _httpx.Client(timeout=10.0, transport=_httpx.HTTPTransport()) as client:
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

            async with httpx.AsyncClient(timeout=600.0, transport=httpx.AsyncHTTPTransport()) as client:
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
            async with httpx.AsyncClient(timeout=5.0, transport=httpx.AsyncHTTPTransport()) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False
