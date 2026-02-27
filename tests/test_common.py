"""公共模块单元测试"""

import os
import tempfile
from pathlib import Path

import pytest

from src.common.config_manager import ConfigManager
from src.common.logger import get_logger
from src.common.file_utils import (
    ensure_dir,
    generate_unique_filename,
    safe_remove,
    get_file_size_mb,
)
from src.common.exceptions import (
    AvatarAgentError,
    ScriptExtractError,
    TTSError,
    ConfigError,
)


class TestLogger:
    """日志模块测试"""

    def test_get_logger(self):
        logger = get_logger("test")
        assert logger is not None
        assert logger.name == "test"

    def test_logger_has_handlers(self):
        logger = get_logger("test_handlers")
        assert len(logger.handlers) > 0

    def test_logger_singleton(self):
        logger1 = get_logger("same_name")
        logger2 = get_logger("same_name")
        assert logger1 is logger2


class TestConfigManager:
    """配置管理器测试"""

    def test_singleton(self):
        config1 = ConfigManager()
        config2 = ConfigManager()
        assert config1 is config2

    def test_get_default(self):
        config = ConfigManager()
        value = config.get("nonexistent_section", "nonexistent_key", "default_val")
        assert value == "default_val"

    def test_get_int_default(self):
        config = ConfigManager()
        value = config.get_int("nonexistent", "key", 42)
        assert value == 42

    def test_get_bool_default(self):
        config = ConfigManager()
        value = config.get_bool("nonexistent", "key", True)
        assert value is True

    def test_get_cosyvoice_url(self):
        config = ConfigManager()
        url = config.get_cosyvoice_url()
        assert url.startswith("http://")
        assert ":" in url

    def test_get_heygem_url(self):
        config = ConfigManager()
        url = config.get_heygem_url()
        assert url.startswith("http://")

    def test_get_tuilionnx_url(self):
        config = ConfigManager()
        url = config.get_tuilionnx_url()
        assert url.startswith("http://")

    def test_get_output_dir(self):
        config = ConfigManager()
        output_dir = config.get_output_dir()
        assert output_dir.exists()

    def test_api_keys_management(self):
        config = ConfigManager()
        original_keys = config.get_api_keys()

        # 添加测试 key
        test_key = "test_key_12345"
        keys = config.add_api_key(test_key)
        assert test_key in keys

        # 不重复添加
        keys2 = config.add_api_key(test_key)
        assert keys2.count(test_key) == 1

        # 删除测试 key
        keys3 = config.remove_api_key(test_key)
        assert test_key not in keys3

        # 恢复原始状态
        config.set("deepseek_apikey", "key", ",".join(original_keys))


class TestFileUtils:
    """文件工具测试"""

    def test_ensure_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = Path(tmpdir) / "sub" / "nested"
            result = ensure_dir(new_dir)
            assert result.exists()
            assert result.is_dir()

    def test_generate_unique_filename(self):
        name1 = generate_unique_filename("wav")
        name2 = generate_unique_filename("wav")
        assert name1 != name2
        assert name1.endswith(".wav")

    def test_generate_unique_filename_with_prefix(self):
        name = generate_unique_filename("mp3", "audio")
        assert name.startswith("audio_")
        assert name.endswith(".mp3")

    def test_safe_remove_nonexistent(self):
        # 应该不抛出异常
        safe_remove("/tmp/definitely_nonexistent_file_xyz.txt")

    def test_get_file_size_mb(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"a" * 1024)
            f.flush()
            size = get_file_size_mb(f.name)
            assert size > 0
            assert size < 1
            os.unlink(f.name)


class TestExceptions:
    """自定义异常测试"""

    def test_base_exception(self):
        with pytest.raises(AvatarAgentError):
            raise AvatarAgentError("测试错误")

    def test_script_exception(self):
        with pytest.raises(AvatarAgentError):
            raise ScriptExtractError("提取失败")

    def test_tts_exception(self):
        with pytest.raises(AvatarAgentError):
            raise TTSError("合成失败")

    def test_config_exception(self):
        with pytest.raises(ConfigError):
            raise ConfigError("配置错误")

    def test_exception_message(self):
        error = ScriptExtractError("test message")
        assert str(error) == "test message"

    def test_exception_hierarchy(self):
        assert issubclass(ScriptExtractError, AvatarAgentError)
        assert issubclass(TTSError, AvatarAgentError)
        assert issubclass(ConfigError, AvatarAgentError)
