from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("favicon.ico", views.favicon, name="favicon"),
    path("logout/", views.admin_logout, name="logout"),
    path("sendmail/", views.contact_email, name="contact_email"),
    path("share/", views.share, name="share"),
    path("_get_next_dirs/", views.next_dirs, name="_next_dirs"),
    path("_get_default_dir_breakdown/", views.default_dir_breakdown, name="_default_dir_breakdown"),  #TODO remove once replaced
    path("share/_start/", views.start_share, name="_start_share"),
    path("share/_start_file/", views.start_file_share, name="_start_file_share"),
    path("share/_upload_chunk/", views.upload_chunk_share, name="_upload_chunk_share"),
    path("share/_finish_file/", views.finish_file_share, name="_finish_file_share"),
    path("share/_finish/", views.finish_share, name="_finish_share"),
]
