from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .utils import md5_hash

import os
import uuid
import shutil
import logging
from pathlib import Path

log = logging.getLogger(__name__)

class ShareModel(models.Model):
    """Stores info on a files share (send from admin to someone) like attributes and status"""
    class Meta:
        verbose_name = _("share model")
        verbose_name_plural = _("share models")
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    public = models.BooleanField(_("public"), default=False)
    email = models.EmailField(_("receiver email"), default=None, null=True)
    email_lang = models.CharField(_("email language"), default=None, null=True)
    message = models.TextField(_("message"), default=None, null=True)
    creation_date = models.DateTimeField(_("creation date"), default=timezone.now)
    expire_date = models.DateTimeField(_("expiration date"), default=None, null=True)
    store_path = models.CharField(_("storage directory"), max_length=4096, default=None, null=True)
    upload_completed = models.BooleanField(_("upload completed"), default=False)
    active = models.BooleanField(_("active"), default=True)  # can be deleted manually
    
    def deactivate(self):
        """Deactivate the share and delete the files on disk"""
        log.info(f"Deactivating share {self.id.hex}")
        self.active = False
        shutil.rmtree(self.store_path)
    
    def __str__(self):
        return f"share-{self.id.hex}"


class RequestModel(models.Model):
    """Stores info on a files request (send from someone to admin) like attributes and status"""
    class Meta:
        verbose_name = _("request model")
        verbose_name_plural = _("request models")
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("sender email"), default=None, null=True)
    email_lang = models.CharField(_("email language"), default=None, null=True)
    message = models.TextField(_("message"), default=None, null=True)
    creation_date = models.DateTimeField(_("creation date"), default=timezone.now)
    expire_date = models.DateTimeField(_("expiration date"), default=None, null=True)
    size_limit = models.PositiveIntegerField(_("upload size limit"), default=None, null=True)
    store_path = models.CharField(_("storage directory"), max_length=4096, default=settings.BASE_STORAGE_PATH)
    upload_completed = models.BooleanField(_("upload completed"), default=False)
    active = models.BooleanField(_("active"), default=True)  # can be deleted manually
    
    def deactivate(self):
            """Deactivate the request and delete the files on disk"""
            log.info(f"Deactivating request {self.id.hex}")
            self.active = False
            shutil.rmtree(self.store_path)
    
    def __str__(self):
        return f"request-{self.id.hex}"


class FileModel(models.Model):
    """Represents a file from a transfer (share/request) with its attributes and status"""
    class Meta:
        verbose_name = _("file share model")
        verbose_name_plural = ("file share models")
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # use as filename for storage
    # either comes from a share or a request: only one with a value, the other should be None
    share = models.ForeignKey(ShareModel, on_delete=models.CASCADE, verbose_name=_("share containing file"), default=None, null=True)
    request = models.ForeignKey(RequestModel, on_delete=models.CASCADE, verbose_name=_("request containing file"), default=None, null=True)
    filename = models.CharField(_("original filename"), max_length=255)  # original filename, not for storage to avoid issues
    file_size = models.PositiveIntegerField(_("file size"), default=None, null=True)
    upload_completed = models.BooleanField(_("upload completed"), default=False)
    last_chunk_date = models.DateTimeField(_("date of last received chunk"), default=timezone.now)
    md5 = models.CharField(_("md5 hex hash"), max_length=32, default=None, null=True)
    antivirus_status = models.TextField(_("antivirus status"), default=None, null=True)
    
    def filepath(self):
        """Returns the file path on disk"""
        if self.share is not None:
            storage_dir = self.share.store_path
        elif self.request is not None:
            storage_dir = self.request.store_path
        else:
            log.error(f"File {self.id.hex} doesn't have an attached share or request")
            return None
        return Path(storage_dir) / (self.id.hex + self.ext())
    
    def ext(self):
        """Get the file extension, including the dot"""
        ext = ""
        if "." in self.filename:
            ext = f".{self.filename.split(".")[-1]}"
        return ext
    
    def on_disk(self):
        """Check if the file exists on disk"""
        filepath = self.filepath()
        return Path.exists(filepath)
    
    def valid_file(self):
        """Check if the file is stored and unaltered"""
        if not self.on_disk():
            return False  # consider invalid if not found
        fpath = self.filepath()
        if self.md5 is None:
            return None  # None if the file has no hash yet
        return self.file_size == os.path.getsize(fpath) and self.md5 == md5_hash(fpath)
    
    def compute_md5(self):
        """Compute the file's md5 hash"""
        self.md5  = md5_hash(self.filepath())
    
    def __str__(self):
        return f"file-{self.id.hex}-[{self.filename}]"
