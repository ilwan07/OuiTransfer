from django.contrib import admin
from django.contrib.auth.models import Group

from .models import ShareModel, RequestModel, FileModel


# Register admin stuff
admin.site.unregister(Group)

# Register models
admin.site.register(ShareModel)
admin.site.register(RequestModel)
