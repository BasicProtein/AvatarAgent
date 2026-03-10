"""Central config.ini access helpers."""

from __future__ import annotations

import configparser
from pathlib import Path
from typing import Optional

from src.common.logger import get_logger

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
CONFIG_PATH = CONFIG_DIR / "config.ini"
CONFIG_TEMPLATE_PATH = CONFIG_DIR / "config_template.ini"


class ConfigManager:
    _instance: Optional["ConfigManager"] = None
    _config: configparser.ConfigParser

    def __new__(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = configparser.ConfigParser()
            cls._instance._load()
        return cls._instance

    def _load(self) -> None:
        if not CONFIG_PATH.exists():
            if CONFIG_TEMPLATE_PATH.exists():
                import shutil

                shutil.copy(CONFIG_TEMPLATE_PATH, CONFIG_PATH)
                logger.info("Created config from template: %s", CONFIG_PATH)
            else:
                logger.warning("Config file not found: %s", CONFIG_PATH)
                return

        self._config.read(str(CONFIG_PATH), encoding="utf-8")
        self._ensure_defaults()
        logger.info("Loaded config file: %s", CONFIG_PATH)

    def _ensure_defaults(self) -> None:
        defaults = {
            "cosyvoice": {
                "host": "127.0.0.1",
                "port": "50000",
                "sample_rate": "22050",
                "device": "gpu",
                "model_dir": "",
            }
        }
        changed = False
        for section, values in defaults.items():
            if not self._config.has_section(section):
                self._config.add_section(section)
                changed = True
            for key, value in values.items():
                if not self._config.has_option(section, key):
                    self._config.set(section, key, value)
                    changed = True
        if changed:
            self._save()

    def reload(self) -> None:
        self._config = configparser.ConfigParser()
        self._load()

    def get(self, section: str, key: str, fallback: str = "") -> str:
        return self._config.get(section, key, fallback=fallback)

    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        return self._config.getint(section, key, fallback=fallback)

    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
        return self._config.getboolean(section, key, fallback=fallback)

    def get_float(self, section: str, key: str, fallback: float = 0.0) -> float:
        return self._config.getfloat(section, key, fallback=fallback)

    def set(self, section: str, key: str, value: str) -> None:
        if not self._config.has_section(section):
            self._config.add_section(section)
        self._config.set(section, key, value)
        self._save()

    def _save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as config_file:
            self._config.write(config_file)
        logger.info("Saved config file.")

    def get_api_keys(self) -> list[str]:
        raw = self.get("deepseek_apikey", "key", "")
        return [key.strip() for key in raw.split(",") if key.strip()]

    def add_api_key(self, key: str) -> list[str]:
        keys = self.get_api_keys()
        if key not in keys:
            keys.append(key)
            self.set("deepseek_apikey", "key", ",".join(keys))
        return keys

    def remove_api_key(self, key: str) -> list[str]:
        keys = [item for item in self.get_api_keys() if item != key]
        self.set("deepseek_apikey", "key", ",".join(keys))
        return keys

    def get_cosyvoice_url(self) -> str:
        host = self.get("cosyvoice", "host", "127.0.0.1")
        port = self.get("cosyvoice", "port", "50000")
        return f"http://{host}:{port}"

    def get_cosyvoice_device(self) -> str:
        device = self.get("cosyvoice", "device", "gpu").strip().lower()
        if device not in {"gpu", "cpu"}:
            return "gpu"
        return device

    def get_cosyvoice_model_dir(self) -> str:
        return self.get("cosyvoice", "model_dir", "").strip()

    def get_heygem_url(self) -> str:
        host = self.get("heygem", "host", "127.0.0.1")
        port = self.get("heygem", "port", "8383")
        return f"http://{host}:{port}"

    def get_heygem_path_mapping(self) -> dict:
        """获取 HeyGem Docker volume 路径映射配置。

        Returns:
            {
                "audio_host_dir": str,       # 宿主机音频目录（空表示不映射）
                "audio_container_dir": str,  # 容器内音频挂载目录
                "video_host_dir": str,       # 宿主机视频目录（空表示不映射）
                "video_container_dir": str,  # 容器内视频挂载目录
            }
        """
        return {
            "audio_host_dir": self.get("heygem", "audio_host_dir", "").strip(),
            "audio_container_dir": self.get("heygem", "audio_container_dir", "/heygem_data/voice/data").strip(),
            "video_host_dir": self.get("heygem", "video_host_dir", "").strip(),
            "video_container_dir": self.get("heygem", "video_container_dir", "/heygem_data/face2face").strip(),
        }

    def get_tuilionnx_url(self) -> str:
        host = self.get("tuilionnx", "host", "127.0.0.1")
        port = self.get("tuilionnx", "port", "8384")
        return f"http://{host}:{port}"

    def get_whisper_device(self) -> str:
        """获取 Whisper ASR 推理设备偏好: 'auto' / 'cuda' / 'cpu'"""
        device = self.get("whisper", "device", "auto").strip().lower()
        if device not in {"auto", "cuda", "cpu"}:
            return "auto"
        return device

    def get_ffmpeg_path(self) -> str:
        path = self.get("ffmpeg", "bin_path", "")
        return path if path else "ffmpeg"

    def get_output_dir(self) -> Path:
        base_dir = self.get("output", "base_dir", "output")
        output_dir = PROJECT_ROOT / base_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def is_cloud_gpu_enabled(self) -> bool:
        return self.get_bool("cloud_gpu", "enabled", False)

    def get_cloud_gpu_config(self) -> dict:
        return {
            "api_url": self.get("cloud_gpu", "api_url", ""),
            "api_key": self.get("cloud_gpu", "api_key", ""),
        }
