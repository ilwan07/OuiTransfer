from django.conf import settings
from django.http import HttpRequest, HttpResponse, Http404, HttpResponseNotAllowed, JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.templatetags.static import static

from .utils import is_path_legal, list_subdirs, path_breakdown, aliased_to_abs_path

import os
from pathlib import Path
import logging

log = logging.getLogger(__name__)


def favicon(request:HttpRequest):
    """Serves the favicon"""
    log.debug("Serving favicon")
    if settings.DEBUG:
        favicon_path = os.path.join(settings.BASE_DIR, "ouitransfer", "static", "ouitransfer", "assets", "favicon.svg")
        if os.path.exists(favicon_path):
            with open(favicon_path, "rb") as f:
                return HttpResponse(f.read(), content_type="image/svg+xml")
        else:
            log.warning("Can't find favicon")
            raise Http404()

    favicon_url = static("ouitransfer/assets/favicon.svg")
    return redirect(favicon_url)


def index(request:HttpRequest):
    """Index page"""
    if request.user.is_staff:
        log.info("Serving admin index")
        return render(request, "ouitransfer/admin_index.html")
    else:
        log.info("Serving user index")
        return render(request, "ouitransfer/index.html")


def admin_logout(request:HttpRequest):
    """Logs the active user out if needed"""
    log.info(f"Logging out user {request.user.username}")
    logout(request)
    return redirect("index")


def contact_email(request:HttpRequest):
    """Redirects to a link to send an email"""
    log.info(f"Redirecting user {request.user.username} to email")
    return HttpResponse(f"<script>window.location.href = 'mailto:{settings.CONTACT_EMAIL}';</script>")


def share(request:HttpRequest):
    """Allows the admin to create a new share"""
    if not request.user.is_staff:
        log.warning(f"User {request.user.username} tried illegal access to share page")
        raise PermissionDenied()
    
    if request.method == "GET":
        return render(request, "ouitransfer/admin_share.html",
                      {"ALLOWED_ROOTS": [f"{cpl[1]}/" if cpl[1] is not None else cpl[0] for cpl in settings.ALLOWED_STORAGE_ROOTS]})
    
    elif request.method == "POST":
        return HttpResponse("TODO")  #TODO post request in share
    
    else:
        log.warning(f"Invalid request method for share: {request.method}")
        return HttpResponseNotAllowed()


def next_dirs(request:HttpRequest):
    """Return a json list of usable directories under the given path, for internal use"""
    if not request.user.is_staff:
        log.warning(f"User {request.user.username} tried illegal access to get next directories")
        raise Http404()
    path = request.GET.get("path", None)
    if path is None:
        log.warning("Tried getting next dir without a path")
        raise Http404()
    realpath = aliased_to_abs_path(path)
    if realpath is None:
        log.warning(f"Tried getting next dir with an invalid path: {path}")
        raise Http404()
    if not realpath.exists() or not is_path_legal(realpath):
        log.warning(f"Tried getting next dir from an inaccessible path: {realpath}")
        raise Http404()
    
    # get writable directories
    response = {"dirs": list_subdirs(realpath)}
    log.debug(f"Served next directories after {realpath}")
    return JsonResponse(response)


def default_dir_breakdown(request:HttpRequest):
    if not request.user.is_staff:
        log.warning(f"User {request.user.username} tried getting default directory breakdown illegally")
        raise Http404()
    path = Path(settings.BASE_STORAGE_PATH)
    if not path.exists() or not is_path_legal(path):
        log.warning("Default directory inaccessible")
        raise Http404()
    breakdown = path_breakdown(path)
    if breakdown is None:
        log.warning("Can't break down default directory")
        raise Http404()

    # return the path elements as json
    return JsonResponse({"breakdown": breakdown})
