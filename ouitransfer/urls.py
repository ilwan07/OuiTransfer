from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("robots.txt", views.robot, name="robot.txt"),
    path("logout/", views.admin_logout, name="logout"),
    path("sendmail/", views.contact_email, name="contact_email"),
]
