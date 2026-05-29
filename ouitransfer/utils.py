from django.conf import settings

import os
import shutil
import hashlib
from pathlib import Path


def md5_hash(file_path:Path, block_size:int=2**25):
    """Compute the MD5 hash by block for large files, defaults to 32MiB blocks"""
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


def norm_path(path:Path):
    """Returns the normalized absolute path as a string (no symlink resolving)"""
    if type(path) != Path:
        path = Path(path)
    return os.path.abspath(path.absolute().as_posix())


def is_path_legal(path:Path):
    """Ensure that the path is legal to save files while avoiding directory traversal"""
    legal_roots = [os.path.abspath(Path(root).absolute().as_posix()) for root in settings.ALLOWED_STORAGE_ROOTS]
    npath = norm_path(path)
    pnpath = Path(npath)
    for root in legal_roots:
        if npath.startswith(root) and pnpath.is_dir() and os.access(pnpath, os.W_OK) and not is_transfer_dir(pnpath):
            return True
    return False


def is_transfer_dir(dir:Path):
    """Is the directory used to save transfers"""
    if type(dir) != Path:
        dir = Path(dir)
    return (dir/f".ouitransfer_dir_{dir.name}").exists()


def list_subdirs(dir:Path):
    """Returns a list of valid subdirectories to access for saving transfers"""
    subdirs = sorted([d.name for d in dir.iterdir() if d.is_dir() and os.access(d, os.W_OK) and not is_transfer_dir(d)],
                     key=lambda s: s.lower().replace(".", "~"))
    return subdirs


def path_breakdown(path:Path):
    """Breaks down a path as a list of path elements starting with a storage root, None if impossible"""
    npath = norm_path(path)
    root_candidates = [cand for cand in settings.ALLOWED_STORAGE_ROOTS if npath.startswith(cand)]
    if root_candidates == []:
        return None
    # take the candidate with deepest tree (arbitrary if using different symlinks)
    root_len = -1
    for cand in root_candidates:
        if len(cand) > root_len:
            root_path = cand
            root_len = len(cand)
    # break down into components, dir by dir, with trailing slashes
    breakdown:list[str] = [root_path] + [f"{dir}/" for dir in npath[root_len:].split("/") if dir!=""]
    if Path(npath).is_file():
        breakdown[-1] = breakdown[-1][:-1]  # remove the last slash if it's a file
    return breakdown
