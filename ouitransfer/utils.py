from django.conf import settings
from django.http import QueryDict
from django.utils import timezone, translation
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.staticfiles import finders
from django.utils.translation import gettext as _

import os
import re
import shutil
import hashlib
import clamd
import socket
import array
import calendar
from threading import Thread
from datetime import datetime, timedelta
from pathlib import Path
import logging

log = logging.getLogger(__name__)


class ClamdUnixSocketFdpass(clamd.ClamdUnixSocket):
    """Allows to scan a file with clamav by passing the file descriptor (see clamd PR #19), enforces max size setting"""
    def fdscan(self, path:str) -> tuple[str, str]:
        try:
            try:
                self._init_socket()
            except clamd.ConnectionError:
                log.error("ClamAV socket unavailable")
                return ("ERROR", "ClamAV socket unavailable.")
            if not os.path.exists(path):
                log.warning(f"Tried to perform antivirus scan on nonexistent path: {path}")
                return ("ERROR", "No such file or directory.")
            if os.path.getsize(path) > settings.ANTIVIRUS_MAX_SIZE:
                return ("FOUND", "Heuristics.Limits.Exceeded.MaxFileSize")
            try:
                fd = os.open(path, os.O_RDONLY)
                try:
                    self.clamd_socket.sendall(b"zFILDES\0")
                    self.clamd_socket.sendmsg(
                        [b"\0"],
                        [(socket.SOL_SOCKET, socket.SCM_RIGHTS,
                        array.array("i", [fd]))]
                    )
                finally:
                    os.close(fd)
                result = self._recv_response().rstrip("\x00")
            finally:
                self._close_socket()
            filename, detail, status = self._parse_response(result)
            return (status, detail)
        except Exception as e:
            log.error(f"Unknown antivirus scan exception: {e}")
            return ("ERROR", "Unknown error.")


def md5_hash(file_path:Path, block_size:int=32*2**20):
    """Compute the MD5 hash by block for large files, defaults to 32MiB blocks (doesn't change the result)"""
    log.debug(f"Computing MD5 for {file_path.as_posix}")
    if not os.path.exists(file_path):
        log.warning(f"File {file_path.as_posix} does not exist")
        return None
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

def antivirus_scan(file_path:Path) -> tuple[int, str]:
    """Perform an antivirus scan on a file, and return a tuple with the status and the detail for use in a file model"""
    log.debug(f"Performing antivirus scan for {file_path}")
    clam = ClamdUnixSocketFdpass()
    if type(file_path) == Path:
        file_path = file_path.as_posix()
    status, detail = clam.fdscan(file_path)
    if status == "ERROR":
        log.error(f"Error when scanning file {file_path}: {detail}")
        return (2, "Error during scan.")
    elif status == "FOUND":
        if detail == "Heuristics.Limits.Exceeded.MaxFileSize":
            return (2, "Too large to scan.")
        else:
            return (3, detail)
    elif status == "OK":
        return (1, "File safe.")
    else:
        log.error(f"Unknown antivirus status for {file_path}: ({status}, {detail})")
        return (2, "Unknown scan result")


def send_email(address:str, template:str, lang:str="en", context:dict={}, sender:str=settings.DEFAULT_FROM_EMAIL):
    """
    Send an email using a thread by providing the templates directory
    The template directory is under the emails directory, and contains template.txt and template.html
    """
    with translation.override(lang):
        subject = get_email_subject(template, lang)
        def send_email_thread():
            try:
                text_content = render_to_string(f"ouitransfer/emails/{template}/template.txt", context=context)
                html_content = render_to_string(f"ouitransfer/emails/{template}/template.html", context=context)
                css_path = finders.find("ouitransfer/css/emails.css")
                if css_path:
                    with open(css_path, "r", encoding="utf-8") as css_file:
                        css = css_file.read()
                    html_content = f"\n<style>\n{css}\n</style>\n" + html_content
                email = EmailMultiAlternatives(_(subject), text_content, sender, [address])
                if html_content is not None:
                    email.attach_alternative(html_content, "text/html")
                email.send()
                log.info(f"Sent email with template {template} to {address}")
            except Exception as e:
                log.error(f'Failure while sending email with subject "{subject}" to {address} with template {template}: {e}')

        context.update({
            "title": subject,
            "base_url": f"{'https' if getattr(settings, 'SECURE_SSL_REDIRECT', False) else 'http'}://{settings.WEB_DOMAIN}",
            "CONTACT_EMAIL": settings.CONTACT_EMAIL,
            "GITHUB_REPO": settings.GITHUB_REPO,
        })
        email_thread = Thread(target=send_email_thread)
        email_thread.daemon = True
        email_thread.start()


def get_email_subject(template, lang):
    """Return the translated email subject associated with a template"""
    with translation.override(lang):
        associations = {
            "send_share": _(f"{settings.OWNER} sent you files!")
        }
        return associations.get(template)


def enough_space(dir:Path, file_size:int):
    """Check if there's enough space in the directory to store file, accounting for safe space"""
    log.debug("Checking available space...")
    if not dir.exists() or not dir.is_dir():
        log.warning(f"Can't find dir {dir.as_posix()}")
        return False  # consider there's no space if the directory doesn't exist
    left = shutil.disk_usage(dir).free - file_size
    enough:bool = left >= settings.STORAGE_SAFE_SPACE
    if not enough:
        log.warning("Disk space full!")
    else:
        log.debug(f"Enough space left: {left}")
    return enough

def space_left(dir:Path):
    """Get space left in dir, accounting for safe space"""
    full_left = shutil.disk_usage(dir).free
    log.debug(f"Space left in {dir}: {full_left}B = {pretty_space(full_left)}, deducting {pretty_space(settings.STORAGE_SAFE_SPACE)}")
    return full_left - settings.STORAGE_SAFE_SPACE

def pretty_space(bytes:int):
    """Returns a string with the specified disk space given in bytes for display with regular units"""
    if bytes < 0:
        bytes = 0
    units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
    n = 0
    unit_space = bytes
    while n < len(units)-1 and unit_space >= 1024:
        n += 1
        unit_space /= 1024
    unit_space = round(unit_space, 2)
    if float(unit_space).is_integer():
        unit_space = int(unit_space)
    res = f"{unit_space} {units[n]}"
    return res


def norm_path(path:Path):
    """Returns the normalized absolute path as a string (no symlink resolving)"""
    if type(path) != Path:
        path = Path(path)
    norm = os.path.abspath(path.absolute().as_posix())
    log.debug(f"Normalized path {path.as_posix()} to {norm}")
    return norm


def is_path_legal(path:Path):
    """Ensure that the path is legal to save files while avoiding directory traversal"""
    if not path:
        return False
    legal_roots = [os.path.abspath(Path(root[0]).absolute().as_posix()) for root in settings.ALLOWED_STORAGE_ROOTS]
    npath = norm_path(path)
    pnpath = Path(npath)
    for root in legal_roots:
        if npath.startswith(root) and pnpath.is_dir() and os.access(pnpath, os.W_OK) and not is_transfer_dir(pnpath):
            after_root = npath[len(root):]
            if settings.ALLOW_DOTFILES or all([not elem.startswith(".") or elem=="." for elem in after_root.split("/")]):
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


def rebuild_path(post:QueryDict):
    """Takes a form and rebuilds the selected path from the selections"""
    index = 0
    built_path = ""
    while True:
        next_elem = post.get(f"path-{index}")
        if next_elem is None:
            return built_path
        built_path += next_elem
        index += 1
        


def validate_email(email:str):
    """Returns True if the given email is valid"""
    if len(email) > 254:
        return False
    email_regex = r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+'
    matching = re.fullmatch(email_regex, email)
    return bool(matching)


def add_months(dt:datetime, n:int):
    """Add n months to a datetime, use the first day of the month after if adding the months result in an invalid day"""
    month_index = dt.month - 1 + n
    year = dt.year + month_index // 12
    month = month_index % 12 + 1

    # use the date if valid, else take the next day
    last_day = calendar.monthrange(year, month)[1]
    if dt.day <= last_day:
        return dt.replace(year=year, month=month, day=dt.day)
    else:
        # take the first of the next month
        month += 1
        if month > 12:
            month = 1
            year += 1
        return dt.replace(year=year, month=month, day=1)
    

def get_posint(val:str):
    """Convert a string to a positive integer, None if not possible"""
    if val is None or not all([c in "0123456789" for c in val]):
        res = None
    else:
        res = int(val)
    return res


def validate_share_form(post:QueryDict):
    """Returns ('ok', dict) with a clean dict if the form is valid, else (error, None) using a short error code"""
    public = post.get("public", "off") == "on"
    # email
    send_email = post.get("send-email", "off") == "on"
    email_address = None
    email_lang = None
    if send_email:
        email_address = post.get("email-address")
        if not email_address or not validate_email(email_address):
            return ("invalid_email", None)
        email_lang = post.get("email-lang")
        if email_lang is None or email_lang not in [lang[0] for lang in settings.LANGUAGES]:
            return ("invalid_email_lang")
    # message
    message = post.get("content", "").strip()
    if message == "":
        message = None
    # expiration date
    expire = post.get("expire", "off") == "on"
    expire_date = None
    if expire:
        delay_unit = post.get("delay-unit")
        if delay_unit not in ("minutes", "hours", "days", "months"):
            return ("invalid_delay_unit", None)
        delay_value = post.get("delay")
        if get_posint(delay_value) is None or int(delay_value) <= 0:
            return ("invalid_delay_value", None)
        delay_value = int(delay_value)
        expire_date = timezone.now()
        if delay_unit == "minutes":
            expire_date += timedelta(minutes=delay_value)
        elif delay_unit == "hours":
            expire_date += timedelta(hours=delay_value)
        elif delay_unit == "days":
            expire_date += timedelta(days=delay_value)
        elif delay_unit == "months":
            expire_date = add_months(expire_date, delay_value)
    # storage path
    store_path = aliased_to_abs_path(rebuild_path(post))
    if not is_path_legal(store_path):
        return ("invalid_path", None)
    store_path = norm_path(store_path)
    # return the clean dict
    return ("ok", {"public":public, "email_address":email_address, "email_lang":email_lang,
                   "message":message, "expire_date":expire_date, "store_path":store_path})
