from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

import uuid
from pathlib import Path


class ShareModel(models.Model):
    """Stores info on a files share (send from admin to someone) like attributes and status"""
    class Meta:
        verbose_name = _("share model")
        verbose_name_plural = _("share models")
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("receiver email"), default=None,null=True)
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
    size_limit = models.IntegerField(_("upload size limit"), default=None, null=True)
    
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
    storage_dir = models.FilePathField(_("storage directory"), default=settings.BASE_STORAGE_PATH)
    upload_completed = models.BooleanField(_("upload completed"), default=False)
    
    def filepath(self):
        """Returns the file path on disk"""
        ext = ""
        if "." in self.filename:
            ext = self.filename.split(".")[-1]
        return Path(self.storage_dir) / (self.id.hex + ext)
    
    def on_disk(self):
        """Check if the file exists on disk"""
        filepath = self.filepath()
        return Path.exists(filepath)
    
    def __str__(self):
        return f"file-{self.id.hex}-'{self.filename}'"
