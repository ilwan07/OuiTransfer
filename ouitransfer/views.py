from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.contrib.auth import logout
from django.shortcuts import render, redirect

import os


def robot(request:HttpRequest):
    """Serves the robot.txt file"""
    file_path = os.path.join(settings.BASE_DIR, "robots.txt")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return HttpResponse(f.read(), content_type="text/plain")
    else:
        return HttpResponse("User-agent: *\nDisallow:", content_type="text/plain")


def index(request:HttpRequest):
    """Index page"""
    if request.user.is_staff:
        return render(request, "ouitransfer/admin_index.html")
    else:
        return render(request, "ouitransfer/index.html")


def admin_logout(request:HttpRequest):
    """Logs the active user out if needed"""
    logout(request)
    return redirect("index")


def contact_email(request:HttpRequest):
    """Redirects to a link to send an email"""
    return HttpResponse(f"<script>window.location.href = 'mailto:{settings.CONTACT_EMAIL}';</script>")
