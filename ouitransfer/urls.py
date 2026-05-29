from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("favicon.ico", views.favicon, name="favicon"),
    path("logout/", views.admin_logout, name="logout"),
    path("sendmail/", views.contact_email, name="contact_email"),
    path("share/", views.share, name="share"),
    path("_get_next_dirs/", views.next_dirs, name="_next_dirs"),
    path("_get_default_dir_breakdown/", views.default_dir_breakdown, name="_default_dir_breakdown"),
]
