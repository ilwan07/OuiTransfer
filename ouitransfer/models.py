from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

import uuid
import datetime


class ShareModel(models.Model):
    """Stores info on a files share (send from admin to someone) like attributes and status"""
    class Meta:
        verbose_name = _("share model")
        verbose_name_plural = _("share models")
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("receiver email"), default=None)
    message = models.TextField(_("message"), default=None)
    expire_date = models.DateTimeField(_("expiration date"), default=None)
    storage_dir = models.FilePathField(_("storage directory"), default=settings.BASE_STORAGE_PATH)

    def __str__(self):
        return self.id.hex


class RequestModel(models.Model):
    """Stores info on a files request (send from someone to admin) like attributes and status"""
    class Meta:
        verbose_name = _("request model")
        verbose_name_plural = _("request models")
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("sender email"), default=None)
    message = models.TextField(_("message"), default=None)
    expire_date = models.DateTimeField(_("expiration date"), default=None)
    storage_dir = models.FilePathField(_("storage directory"), default=settings.BASE_STORAGE_PATH)
    size_limit = models.IntegerField(_("upload size limit"), default=None)
