"""配置管理模块 - 基于 configparser 读写 config.ini"""

import configparser
from pathlib import Path
from typing import Optional

from src.common.logger import get_logger

logger = get_logger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
CONFIG_PATH = CONFIG_DIR / "config.ini"
CONFIG_TEMPLATE_PATH = CONFIG_DIR / "config_template.ini"


class ConfigManager:
    """统一配置管理器

    单例模式，全局共享同一个配置实例。
    读写 config/config.ini 文件。
    """

    _instance: Optional["ConfigManager"] = None
    _config: configparser.ConfigParser

    def __new__(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = configparser.ConfigParser()
            cls._instance._load()
        return cls._instance

    def _load(self) -> None:
        """加载配置文件，若不存在则从模板创建"""
        if not CONFIG_PATH.exists():
            if CONFIG_TEMPLATE_PATH.exists():
                import shutil
                shutil.copy(CONFIG_TEMPLATE_PATH, CONFIG_PATH)
                logger.info(f"已从模板创建配置文件: {CONFIG_PATH}")
            else:
                logger.warning(f"配置文件和模板均不存在: {CONFIG_PATH}")
                return

        self._config.read(str(CONFIG_PATH), encoding="utf-8")
        logger.info(f"已加载配置文件: {CONFIG_PATH}")

    def reload(self) -> None:
        """重新加载配置文件"""
        self._config = configparser.ConfigParser()
        self._load()

    def get(self, section: str, key: str, fallback: str = "") -> str:
        """获取配置项"""
        return self._config.get(section, key, fallback=fallback)

    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        """获取整数配置项"""
        return self._config.getint(section, key, fallback=fallback)

    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
        """获取布尔配置项"""
        return self._config.getboolean(section, key, fallback=fallback)

    def get_float(self, section: str, key: str, fallback: float = 0.0) -> float:
        """获取浮点数配置项"""
        return self._config.getfloat(section, key, fallback=fallback)

    def set(self, section: str, key: str, value: str) -> None:
        """设置配置项并持久化"""
        if not self._config.has_section(section):
            self._config.add_section(section)
        self._config.set(section, key, value)
        self._save()

    def _save(self) -> None:
        """将配置写入文件"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            self._config.write(f)
        logger.info("配置已保存")

    # ---- API Key 管理 ----

    def get_api_keys(self) -> list[str]:
        """获取所有 Deepseek API Key"""
        raw = self.get("deepseek_apikey", "key", "")
        return [k.strip() for k in raw.split(",") if k.strip()]

    def add_api_key(self, key: str) -> list[str]:
        """添加一个 API Key"""
        keys = self.get_api_keys()
        if key not in keys:
            keys.append(key)
            self.set("deepseek_apikey", "key", ",".join(keys))
        return keys

    def remove_api_key(self, key: str) -> list[str]:
        """删除一个 API Key"""
        keys = self.get_api_keys()
        keys = [k for k in keys if k != key]
        self.set("deepseek_apikey", "key", ",".join(keys))
        return keys

    # ---- 服务地址获取 ----

    def get_cosyvoice_url(self) -> str:
        """获取 CosyVoice 服务地址"""
        host = self.get("cosyvoice", "host", "127.0.0.1")
        port = self.get("cosyvoice", "port", "5000")
        return f"http://{host}:{port}"

    def get_heygem_url(self) -> str:
        """获取 HeyGem 服务地址"""
        host = self.get("heygem", "host", "127.0.0.1")
        port = self.get("heygem", "port", "8383")
        return f"http://{host}:{port}"

    def get_tuilionnx_url(self) -> str:
        """获取 TuiliONNX 服务地址"""
        host = self.get("tuilionnx", "host", "127.0.0.1")
        port = self.get("tuilionnx", "port", "8384")
        return f"http://{host}:{port}"

    def get_ffmpeg_path(self) -> str:
        """获取 FFmpeg 可执行文件路径"""
        path = self.get("ffmpeg", "bin_path", "")
        return path if path else "ffmpeg"

    def get_output_dir(self) -> Path:
        """获取输出文件目录"""
        base = self.get("output", "base_dir", "output")
        output_dir = PROJECT_ROOT / base
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def is_cloud_gpu_enabled(self) -> bool:
        """检查是否启用云端 GPU"""
        return self.get_bool("cloud_gpu", "enabled", False)

    def get_cloud_gpu_config(self) -> dict:
        """获取云端 GPU 配置"""
        return {
            "api_url": self.get("cloud_gpu", "api_url", ""),
            "api_key": self.get("cloud_gpu", "api_key", ""),
        }
