from django.conf import settings
from django.http import HttpRequest, HttpResponse, Http404, HttpResponseNotAllowed,JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.templatetags.static import static

from .utils import is_path_legal

import os
from pathlib import Path


def favicon(request:HttpRequest):
    """Serves the favicon"""
    if settings.DEBUG:
        favicon_path = os.path.join(settings.BASE_DIR, "ouitransfer", "static", "ouitransfer", "assets", "favicon.svg")
        if os.path.exists(favicon_path):
            with open(favicon_path, "rb") as f:
                return HttpResponse(f.read(), content_type="image/svg+xml")
        else:
            raise Http404()

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
    """Allows the admin to create a new share"""
    if not request.user.is_staff:
        raise PermissionDenied()
    
    if request.method == "GET":
        return render(request, "ouitransfer/admin_share.html")
    
    elif request.method == "POST":
        return HttpResponse("TODO")  #TODO
    
    else:
        return HttpResponseNotAllowed()

def next_dirs(request:HttpRequest):
    """Return a json list of usable directories under the given path, for internal use"""
    if not request.user.is_staff:
        raise PermissionDenied()
    path = request.GET.get("path", None)
    if path is None:
        raise Http404()
    path = Path(path)
    if not path.exists():
        raise Http404()
    if not is_path_legal(path):
        raise PermissionDenied()
    
    # get writable directories
    subdirs = sorted([d.name for d in path.iterdir() if d.is_dir() and os.access(d, os.W_OK)], key=lambda s: s.lower().replace(".", "~"))
    response = {"dirs": subdirs}
    return JsonResponse(response)
