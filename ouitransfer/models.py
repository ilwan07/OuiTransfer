from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .utils import md5_hash, enough_space

import uuid
from pathlib import Path


class ShareModel(models.Model):
    """Stores info on a files share (send from admin to someone) like attributes and status"""
    class Meta:
        verbose_name = _("share model")
        verbose_name_plural = _("share models")
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("receiver email"), default=None, null=True)
    message = models.TextField(_("message"), default=None, null=True)
    expire_date = models.DateTimeField(_("expiration date"), default=None, null=True)

    def __str__(self):
        return f"share-{self.id.hex}"


class RequestModel(models.Model):
    """Stores info on a files request (send from someone to admin) like attributes and status"""
    class Meta:
        verbose_name = _("request model")
        verbose_name_plural = _("request models")
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("sender email"), default=None, null=True)
    message = models.TextField(_("message"), default=None, null=True)
    expire_date = models.DateTimeField(_("expiration date"), default=None, null=True)
    size_limit = models.PositiveIntegerField(_("upload size limit"), default=None, null=True)
    
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
    storage_dir = models.FilePathField(_("storage directory"), default=settings.BASE_STORAGE_PATH)
    upload_completed = models.BooleanField(_("upload completed"), default=False)
    md5 = models.CharField(_("md5 hex hash"), max_length=32)
    
    def filepath(self):
        """Returns the file path on disk"""
        ext = ""
        if "." in self.filename:
            ext = self.filename.split(".")[-1]
        return Path(self.storage_dir) / (self.id.hex + ext)
    
    def space_to_write(self):
        """Check if there's enough space to write the file on disk"""
        return enough_space(self.storage_dir, self.file_size)
    
    def on_disk(self):
        """Check if the file exists on disk"""
        filepath = self.filepath()
        return Path.exists(filepath)
    
    def valid_file(self):
        """Check if the file is stored and unaltered"""
        if not self.on_disk():
            return False  # consider invalid if not found
        return self.md5 == md5_hash(self.filepath())
    
    def __str__(self):
        return f"file-{self.id.hex}-[{self.filename}]"
