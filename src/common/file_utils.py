"""文件工具函数模块"""

import os
import uuid
import shutil
from pathlib import Path
from typing import Optional

from src.common.logger import get_logger

logger = get_logger(__name__)


def ensure_dir(path: str | Path) -> Path:
    """确保目录存在，不存在则创建

    Args:
        path: 目录路径

    Returns:
        Path 对象
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def generate_unique_filename(extension: str = "", prefix: str = "") -> str:
    """生成唯一文件名

    Args:
        extension: 文件扩展名（不含 .）
        prefix: 文件名前缀

    Returns:
        唯一文件名
    """
    name = f"{prefix}_{uuid.uuid4().hex[:8]}" if prefix else uuid.uuid4().hex[:12]
    if extension:
        ext = extension if extension.startswith(".") else f".{extension}"
        return f"{name}{ext}"
    return name


def safe_remove(path: str | Path) -> bool:
    """安全删除文件或目录

    Args:
        path: 文件或目录路径

    Returns:
        是否成功删除
    """
    try:
        p = Path(path)
        if p.is_file():
            p.unlink()
        elif p.is_dir():
            shutil.rmtree(p)
        else:
            return False
        logger.info(f"已删除: {path}")
        return True
    except Exception as e:
        logger.error(f"删除失败 {path}: {e}")
        return False


def get_file_size_mb(path: str | Path) -> float:
    """获取文件大小（MB）"""
    return Path(path).stat().st_size / (1024 * 1024)


def list_files_by_extension(directory: str | Path, extensions: list[str]) -> list[Path]:
    """按扩展名列出目录下的文件

    Args:
        directory: 目标目录
        extensions: 扩展名列表，如 [".mp4", ".avi"]

    Returns:
        匹配的文件路径列表
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        return []

    ext_set = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in extensions}
    return sorted(
        [f for f in dir_path.iterdir() if f.is_file() and f.suffix.lower() in ext_set],
        key=lambda x: x.name,
    )


def copy_file(src: str | Path, dst: str | Path) -> Path:
    """复制文件

    Args:
        src: 源文件路径
        dst: 目标路径（文件或目录）

    Returns:
        目标文件 Path
    """
    src_path = Path(src)
    dst_path = Path(dst)

    if dst_path.is_dir():
        dst_path = dst_path / src_path.name

    dst_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src_path), str(dst_path))
    logger.info(f"已复制: {src} -> {dst_path}")
    return dst_path
