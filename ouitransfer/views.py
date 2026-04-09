from django.conf import settings
from django.http import HttpRequest, HttpResponse, Http404
from django.core.exceptions import PermissionDenied
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.templatetags.static import static

import os


def favicon(request:HttpRequest):
    """Serves the favicon"""
    if settings.DEBUG:
        favicon_path = os.path.join(settings.BASE_DIR, "ouitransfer", "static", "ouitransfer", "assets", "favicon.svg")
        if os.path.exists(favicon_path):
            with open(favicon_path, "rb") as f:
                return HttpResponse(f.read(), content_type="image/svg+xml")
        else:
            raise Http404("Favicon not found")

    favicon_url = static("ouitransfer/assets/favicon.svg")
    return redirect(favicon_url)


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


def share(request:HttpRequest):
    """Allows the admin to share new files"""
    if not request.user.is_staff:
        raise PermissionDenied("You're not an admin")
    
    return HttpResponse("TODO")
