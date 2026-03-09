"""自定义异常定义"""


class AvatarAgentError(Exception):
    """AvatarAgent 基础异常类"""
    pass


class ScriptExtractError(AvatarAgentError):
    """文案提取异常"""
    pass


class ScriptRewriteError(AvatarAgentError):
    """文案仿写异常"""
    pass


class TTSError(AvatarAgentError):
    """语音合成异常"""
    pass


class ASRError(AvatarAgentError):
    """语音识别异常"""
    pass


class AvatarGenerateError(AvatarAgentError):
    """数字人生成异常"""
    pass


class VideoProcessError(AvatarAgentError):
    """视频处理异常"""
    pass


class SubtitleError(AvatarAgentError):
    """字幕处理异常"""
    pass


class BGMError(AvatarAgentError):
    """背景音乐处理异常"""
    pass


class CoverError(AvatarAgentError):
    """封面生成异常"""
    pass


class ComplianceCheckError(AvatarAgentError):
    """合规审查异常"""
    pass


class UploadError(AvatarAgentError):
    """平台发布异常"""
    pass


class ConfigError(AvatarAgentError):
    """配置异常"""
    pass


class CloudGPUError(AvatarAgentError):
    """云端 GPU 异常"""
    pass
