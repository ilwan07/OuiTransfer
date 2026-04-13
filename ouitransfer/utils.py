from django.conf import settings

import os
import shutil
import hashlib
from pathlib import Path


def md5_hash(file_path:Path, block_size:int=2**25):
    """Compute the MD5 hash by blocks for large files, defaults to 32MiB blocks"""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        while True:
            block = f.read(block_size)
            if not block:
                break
            hasher.update(block)
    return hasher.hexdigest()


def enough_space(dir:Path, file_size:int) -> bool:
    """Check if there's enough space in the directory to store file, accounting for safe space"""
    if not dir.exists() or not dir.is_dir():
        return False  # consider there's no space if the directory doesn't exist
    return shutil.disk_usage(dir).free - file_size >= settings.STORAGE_SAFE_SPACE


def is_path_legal(path:Path):
    """Ensure that the path is legal to save files while avoiding directory traversal"""
    legal_roots = [os.path.abspath(Path(root).absolute().as_posix()) for root in settings.ALLOWED_STORAGE_ROOTS]
    norm_path = os.path.abspath(path.absolute().as_posix())
    for root in legal_roots:
        if norm_path.startswith(root):
            return True
    return False
