from django.conf import settings

import os
import shutil
import hashlib
from pathlib import Path
import logging

log = logging.getLogger(__name__)


def md5_hash(file_path:Path, block_size:int=2**25):
    """Compute the MD5 hash by block for large files, defaults to 32MiB blocks"""
    log.debug(f"Computing MD5 for {file_path.as_posix}")
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        while True:
            block = f.read(block_size)
            if not block:
                break
            hasher.update(block)
    result = hasher.hexdigest()
    log.debug(f"Hash result: {result}")
    return result


def enough_space(dir:Path, file_size:int) -> bool:
    """Check if there's enough space in the directory to store file, accounting for safe space"""
    log.debug("Checking available space...")
    if not dir.exists() or not dir.is_dir():
        log.warning(f"Can't find dir {dir.as_posix()}")
        return False  # consider there's no space if the directory doesn't exist
    left = shutil.disk_usage(dir).free - file_size
    enough = left >= settings.STORAGE_SAFE_SPACE
    if not enough:
        log.warning("Disk space full!")
    else:
        log.debug(f"Enough space left: {left}")
    return enough


def norm_path(path:Path):
    """Returns the normalized absolute path as a string (no symlink resolving)"""
    if type(path) != Path:
        path = Path(path)
    norm = os.path.abspath(path.absolute().as_posix())
    log.debug(f"Normalized path {path.as_posix()} to {norm}")
    return norm


def is_path_legal(path:Path):
    """Ensure that the path is legal to save files while avoiding directory traversal"""
    legal_roots = [os.path.abspath(Path(root[0]).absolute().as_posix()) for root in settings.ALLOWED_STORAGE_ROOTS]
    npath = norm_path(path)
    pnpath = Path(npath)
    for root in legal_roots:
        if npath.startswith(root) and pnpath.is_dir() and os.access(pnpath, os.W_OK) and not is_transfer_dir(pnpath):
            if settings.ALLOW_DOTFILES or all([not elem.startswith(".") or elem=="." for elem in npath.split("/")]):
                return True
    log.warning(f"Blocked illegal path: {path.as_posix()}")
    return False


def is_transfer_dir(dir:Path):
    """Is the directory used to save transfers"""
    if type(dir) != Path:
        dir = Path(dir)
    return (dir/f".ouitransfer_dir_{dir.name}").exists()


def list_subdirs(dir:Path):
    """Returns a list of valid subdirectories to access for saving transfers"""
    log.debug(f"Listing subdirectories of {dir.as_posix()}...")
    subdirs = sorted([d.name for d in dir.iterdir() if d.is_dir() and os.access(d, os.W_OK) and not is_transfer_dir(d)
                      and (settings.ALLOW_DOTFILES or not d.name.startswith("."))],
                     key=lambda s: s.lower().replace(".", "~"))  # sort dotfiles at the end
    log.debug(f"Listed directories {subdirs}")
    return subdirs


def path_breakdown(path:Path):
    """Breaks down a path as a list of path elements starting with a storage root (eventally aliased), None if impossible"""
    npath = norm_path(path)
    root_cpl_candidates = [cpl for cpl in settings.ALLOWED_STORAGE_ROOTS if npath.startswith(cpl[0])]
    if root_cpl_candidates == []:
        log.warning(f"Can't break down path: {path.as_posix()}")
        return None
    # take the candidate with deepest tree (arbitrary if using different symlinks)
    root_len = -1
    for cand in root_cpl_candidates:
        if len(cand[0]) > root_len:
            root_path = f"{cand[1]}/" if cand[1] is not None else cand[0]
            root_len = len(cand[0])
    # break down into components, dir by dir, with trailing slashes
    breakdown:list[str] = [root_path] + [f"{dir}/" for dir in npath[root_len:].split("/") if dir!=""]
    if Path(npath).is_file():
        breakdown[-1] = breakdown[-1][:-1]  # remove the last slash if it's a file (should not happen for our use case but we never know)
    return breakdown


def aliased_to_abs_path(aliased:str):
    """Takes a potentially aliased path, and returns the real absolute path associated if it exists"""
    if len(aliased) == 0:
        log.warning("Processing empty path alias")
        return None
    if aliased[0] == "/":
        return Path(aliased)
    prefix = aliased.split("/")[0]
    suffix = "/".join(aliased.split("/")[1:])
    for cpl in settings.ALLOWED_STORAGE_ROOTS:
        if cpl[1] == prefix:
            return Path(f"{cpl[0]}/{suffix}")
    log.warning(f"Inexistant path alias: {aliased}")
    return None
