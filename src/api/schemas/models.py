"""Pydantic 请求/响应数据模型"""

from typing import Optional
from pydantic import BaseModel, Field


# ========== 通用响应 ==========

class StatusResponse(BaseModel):
    """通用状态响应"""
    status: str = Field(..., description="状态: success/error")
    message: str = Field("", description="提示信息")
    data: dict | None = Field(None, description="返回数据")


# ========== 文案模块 ==========

class ExtractRequest(BaseModel):
    """文案提取请求"""
    video_url: str = Field(..., description="视频链接")


class ExtractResponse(BaseModel):
    """文案提取响应"""
    text: str = Field(..., description="提取的文案")


class RewriteRequest(BaseModel):
    """文案仿写请求"""
    text: str = Field(..., description="原始文案")
    api_key: str = Field(..., description="Deepseek API Key")
    mode: str = Field("auto", description="仿写模式: auto/custom")
    prompt: str = Field("", description="自定义指令（mode=custom 时必填）")


class DescriptionRequest(BaseModel):
    """视频描述生成请求"""
    text: str = Field(..., description="口播文案")
    api_key: str = Field(..., description="Deepseek API Key")


# ========== 合规审查模块 ==========

class ComplianceCheckRequest(BaseModel):
    """合规审查请求"""
    text: str = Field(..., description="待审查文案")
    api_key: str = Field(..., description="Deepseek API Key")


class ProhibitedWordItem(BaseModel):
    """违禁词命中项"""
    word: str = Field(..., description="违禁词")
    position: int = Field(..., description="出现位置")
    category: str = Field(..., description="违禁词类别")


class AiSuggestionItem(BaseModel):
    """AI 合规建议项"""
    original: str = Field(..., description="问题原文")
    suggestion: str = Field(..., description="建议修改")
    reason: str = Field(..., description="违规原因")


class ComplianceCheckResponse(BaseModel):
    """合规审查响应"""
    passed: bool = Field(..., description="是否通过审查")
    prohibited_words: list[ProhibitedWordItem] = Field(default_factory=list, description="命中的违禁词")
    ai_suggestions: list[AiSuggestionItem] = Field(default_factory=list, description="AI 合规建议")
    revised_text: str = Field("", description="修正后的文案")


# ========== 音频模块 ==========

class VoiceItem(BaseModel):
    """音色信息"""
    name: str
    path: str


class SynthesizeRequest(BaseModel):
    """语音合成请求"""
    text: str = Field(..., description="待合成文本")
    voice_id: int = Field(0, description="音色索引")
    speed: float = Field(1.0, ge=0.5, le=2.0, description="语速倍率")


class SynthesizeResponse(BaseModel):
    """语音合成响应（含服务端绝对路径，供后续步骤使用）"""
    audio_path: str = Field(..., description="服务端音频绝对路径")
    audio_url: str = Field(..., description="HTTP 可访问的音频 URL")
    duration: float = Field(0.0, description="音频时长（秒）")


class VoiceTrainRequest(BaseModel):
    """声音训练请求"""
    name: str = Field(..., description="音色名称，10字以内")
    audio_path: str = Field(..., description="参考音频服务端路径（已上传）")


# ========== 数字人模块 ==========

class AvatarModel(BaseModel):
    """数字人模型信息"""
    name: str
    path: str = ""


class AvatarGenerateRequest(BaseModel):
    """数字人生成请求"""
    model_name: str = Field(..., description="模型名称/ID")
    audio_path: str = Field(..., description="音频文件路径")
    engine: str = Field("tuilionnx", description="引擎: heygem/tuilionnx")
    batch_size: int = Field(4, ge=1, le=16)
    sync_offset: int = Field(0, ge=-10, le=10)
    scale_h: float = Field(1.6)
    scale_w: float = Field(3.6)
    compress_inference: bool = Field(False)
    beautify_teeth: bool = Field(False)
    add_watermark: bool = Field(True)


class AvatarSaveRequest(BaseModel):
    """形象保存请求"""
    name: str = Field(..., description="形象名称，10字以内")
    video_path: str = Field(..., description="人脸视频服务端路径（已上传）")
    description: str = Field("", description="形象描述（可选）")


# ========== 视频后期模块 ==========

class SubtitleStyle(BaseModel):
    """字幕样式"""
    font_family: str = Field("Microsoft YaHei")
    font_size: int = Field(11)
    font_color: str = Field("#FFFFFF")
    outline_color: str = Field("#000000")
    bottom_margin: int = Field(60)


class SubtitleRequest(BaseModel):
    """字幕生成/添加请求"""
    video_path: str = Field(..., description="视频路径")
    text: str = Field("", description="口播文案（可选）")
    api_key: str = Field("", description="API Key（用于 ASR）")
    style: SubtitleStyle = Field(default_factory=SubtitleStyle)


class BGMRequest(BaseModel):
    """BGM 添加请求"""
    video_path: str = Field(..., description="视频路径")
    bgm_name: str = Field("", description="BGM 名称（为空则随机）")
    volume: float = Field(0.5, ge=0, le=1.0, description="BGM 音量")


class CoverRequest(BaseModel):
    """封面生成请求"""
    video_path: str = Field(..., description="视频路径")
    text: str = Field("", description="封面文案")
    script_text: str = Field("", description="口播文案（AI 模式用于生成封面标题）")
    highlight_words: str = Field("", description="高亮词（逗号分隔）")
    use_ai: bool = Field(False, description="是否使用 AI 生成文案")
    api_key: str = Field("", description="Deepseek API Key（AI 模式必填）")
    font_family: str = Field("SimHei")
    font_size: int = Field(60)
    font_color: str = Field("#FFFFFF")
    highlight_color: str = Field("#FFD600")
    position: str = Field("bottom", description="文字位置: top/center/bottom")
    frame_time: float | None = Field(None, description="抽帧时间点（秒）")


# ========== 发布模块 ==========

class PublishRequest(BaseModel):
    """发布请求"""
    video_path: str = Field(..., description="视频路径")
    description: str = Field(..., description="视频描述")
    cover_path: str = Field("", description="封面路径（可选）")
    tags: list[str] = Field(default_factory=list, description="话题标签")


# ========== 全流程 ==========

class PipelineRequest(BaseModel):
    """全流程执行请求"""
    video_url: str = Field(..., description="对标视频链接")
    api_key: str = Field(..., description="Deepseek API Key")
    voice_id: int = Field(0)
    model_name: str = Field("")
    speed: float = Field(1.0)
    skip_bgm: bool = Field(False)
    create_cover: bool = Field(True)
    publish_platforms: list[str] = Field(default_factory=list)
    description: str = Field("")
    avatar_engine: str = Field("tuilionnx")
    subtitle_style: SubtitleStyle = Field(default_factory=SubtitleStyle)
    bgm_volume: float = Field(0.5)


# ========== 配置模块 ==========

class ApiKeyRequest(BaseModel):
    """API Key 操作请求"""
    key: str = Field(..., description="API Key 值")
