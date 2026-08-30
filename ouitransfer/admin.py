from django.contrib import admin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from .models import ShareModel, RequestModel, FileModel

class FileModelInLine(admin.TabularInline):
    model = FileModel
    extra = 0
    show_change_link = True
    classes = []
    fields = ["filename", "file_size", "md5", "antivirus_detail", "upload_completed"]


class ShareModelAdmin(admin.ModelAdmin):
    fieldsets = [
        (_("General"), {"fields": ["active", "message", "creation_date", "expire_date", "store_path"]}),
        (_("Sharing"), {"fields": ["public", "email", "email_lang"]}),
        (_("Misc"), {"fields": ["upload_completed", "last_chunk_date"]}),
    ]
    inlines = [FileModelInLine]
    list_display = ["id", "active", "public", "creation_date", "expire_date", "store_path"]
    list_filter = ["active", "public", "email", "upload_completed"]
    search_fields = ["message", "store_path"]

class RequestModelAdmin(admin.ModelAdmin):
    fieldsets = [
        (_("General"), {"fields": ["active", "message", "creation_date", "expire_date", "store_path"]}),
        (_("Sharing"), {"fields": ["email", "email_lang"]}),
        (_("Misc"), {"fields": ["upload_completed", "last_chunk_date"]}),
    ]
    inlines = [FileModelInLine]
    list_display = ["id", "active", "creation_date", "expire_date", "store_path"]
    list_filter = ["active", "email", "upload_completed"]
    search_fields = ["message", "store_path"]

class FileModelAdmin(admin.ModelAdmin):
    fieldsets = [
        (_("Origin"), {"fields": ["share", "request"]}),
        (_("General"), {"fields": ["filename", "file_size", "md5", "upload_completed"]}),
        (_("Antivirus"), {"fields": ["antivirus_status", "antivirus_detail"]}),
    ]
    list_display = ["id", "filename", "file_size", "md5", "antivirus_detail"]
    list_filter = ["upload_completed", "antivirus_status"]
    search_fields = ["filename", "antivirus_detail"]


# Register admin stuff
admin.site.unregister(Group)

# Register models
admin.site.register(ShareModel, ShareModelAdmin)
admin.site.register(RequestModel, RequestModelAdmin)
admin.site.register(FileModel, FileModelAdmin)
