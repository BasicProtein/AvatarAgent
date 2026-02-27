"""全流程编排器

一键执行完整的视频生产流水线：
文案提取 → 仿写 → 语音合成 → 数字人 → 字幕 → BGM → 封面 → 发布
"""

from typing import Optional

from src.common.logger import get_logger
from src.common.config_manager import ConfigManager
from src.common.exceptions import AvatarAgentError

logger = get_logger(__name__)


class PipelineOrchestrator:
    """一键全流程编排器

    将所有模块串联为完整的视频生产流水线，
    支持每一步的独立调试和跳过。
    """

    def __init__(self) -> None:
        self.config = ConfigManager()

    async def run_full_pipeline(
        self,
        video_url: str,
        api_key: str,
        voice_id: int = 0,
        model_name: str = "",
        speed: float = 1.0,
        skip_bgm: bool = False,
        create_cover: bool = True,
        publish_platforms: list[str] | None = None,
        description: str = "",
        avatar_engine: str = "tuilionnx",
        subtitle_style: dict | None = None,
        bgm_volume: float = 0.5,
        cover_config: dict | None = None,
    ) -> dict:
        """执行完整的视频生产流水线

        Args:
            video_url: 对标视频链接
            api_key: Deepseek API Key
            voice_id: 音色 ID
            model_name: 数字人模型名称
            speed: 语速
            skip_bgm: 是否跳过 BGM
            create_cover: 是否生成封面
            publish_platforms: 发布平台列表 ["douyin", "xiaohongshu", "shipinhao"]
            description: 视频描述（为空则自动生成）
            avatar_engine: 数字人引擎 ("heygem" / "tuilionnx")
            subtitle_style: 字幕样式配置
            bgm_volume: BGM 音量
            cover_config: 封面配置

        Returns:
            流水线执行结果字典
        """
        result = {
            "status": "running",
            "steps": {},
        }

        try:
            # ========== Step 1: 提取文案 ==========
            logger.info("Step 1/8: 提取对标文案")
            from src.script.extractor import ScriptExtractor
            extractor = ScriptExtractor()
            original_text = extractor.extract_from_url(video_url)
            result["steps"]["extract"] = {"status": "done", "text": original_text}

            # ========== Step 2: 文案仿写 ==========
            logger.info("Step 2/8: AI 文案仿写")
            from src.script.rewriter import ScriptRewriter
            rewriter = ScriptRewriter()
            rewritten_text = await rewriter.rewrite_auto(original_text, api_key)
            result["steps"]["rewrite"] = {"status": "done", "text": rewritten_text}

            # ========== Step 3: 语音合成 ==========
            logger.info("Step 3/8: 语音合成")
            from src.audio.tts import TTSEngine
            tts = TTSEngine()
            audio_path = await tts.synthesize(rewritten_text, voice_id, speed)
            result["steps"]["tts"] = {"status": "done", "audio_path": audio_path}

            # ========== Step 4: 数字人视频生成 ==========
            logger.info("Step 4/8: 数字人视频生成")
            if avatar_engine == "heygem":
                from src.avatar.heygem import HeyGemEngine
                engine = HeyGemEngine()
                avatar_result = await engine.generate(model_name, audio_path)
            else:
                from src.avatar.heygem import TuiliONNXEngine
                engine = TuiliONNXEngine()
                avatar_result = await engine.generate(
                    face_id=model_name, audio_path=audio_path
                )
            video_path = avatar_result["video_path"]
            result["steps"]["avatar"] = {"status": "done", "video_path": video_path}

            # ========== Step 5: 字幕生成与添加 ==========
            logger.info("Step 5/8: 生成字幕")
            from src.video.subtitle import SubtitleGenerator
            subtitle_gen = SubtitleGenerator()
            srt_path = await subtitle_gen.generate_srt(audio_path, rewritten_text, api_key)
            style = subtitle_style or {}
            video_path = await subtitle_gen.add_to_video(
                video_path, srt_path, **style
            )
            result["steps"]["subtitle"] = {"status": "done", "video_path": video_path}

            # ========== Step 6: 背景音乐 ==========
            if not skip_bgm:
                logger.info("Step 6/8: 添加背景音乐")
                from src.video.bgm import BGMManager
                bgm_mgr = BGMManager()
                video_path = await bgm_mgr.add_random_bgm(video_path, bgm_volume)
                result["steps"]["bgm"] = {"status": "done", "video_path": video_path}
            else:
                logger.info("Step 6/8: 跳过 BGM")
                result["steps"]["bgm"] = {"status": "skipped"}

            # ========== Step 7: 封面生成 ==========
            cover_path = ""
            if create_cover:
                logger.info("Step 7/8: 生成封面")
                from src.video.cover import CoverGenerator
                cover_gen = CoverGenerator()
                cover_cfg = cover_config or {}
                cover_path = await cover_gen.generate(
                    video_path, text=rewritten_text[:30], **cover_cfg
                )
                result["steps"]["cover"] = {"status": "done", "cover_path": cover_path}
            else:
                logger.info("Step 7/8: 跳过封面")
                result["steps"]["cover"] = {"status": "skipped"}

            # ========== Step 8: 多平台发布 ==========
            if publish_platforms:
                logger.info(f"Step 8/8: 发布到 {publish_platforms}")

                # 生成视频描述
                if not description:
                    description = await rewriter.generate_description(
                        rewritten_text, api_key
                    )

                from src.uploader.douyin import DouyinUploader
                from src.uploader.xiaohongshu import XiaohongshuUploader
                from src.uploader.shipinhao import ShipinhaoUploader

                uploaders = {
                    "douyin": DouyinUploader,
                    "xiaohongshu": XiaohongshuUploader,
                    "shipinhao": ShipinhaoUploader,
                }

                publish_results = {}
                for platform in publish_platforms:
                    if platform in uploaders:
                        uploader = uploaders[platform]()
                        try:
                            success = await uploader.publish(
                                video_path, description, cover_path
                            )
                            publish_results[platform] = "success" if success else "failed"
                        except Exception as e:
                            publish_results[platform] = f"error: {e}"
                            logger.error(f"发布到 {platform} 失败: {e}")

                result["steps"]["publish"] = {
                    "status": "done",
                    "results": publish_results,
                }
            else:
                logger.info("Step 8/8: 跳过发布")
                result["steps"]["publish"] = {"status": "skipped"}

            result["status"] = "completed"
            result["video_path"] = video_path
            logger.info("全流程执行完成!")

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            logger.error(f"流水线执行失败: {e}")

        return result
