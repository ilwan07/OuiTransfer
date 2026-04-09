from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("favicon.ico", views.favicon, name="favicon"),
    path("logout/", views.admin_logout, name="logout"),
    path("sendmail/", views.contact_email, name="contact_email"),
    path("share/", views.share, name="share"),
]
