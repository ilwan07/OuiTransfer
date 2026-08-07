from django.conf import settings
from django.http import HttpRequest, HttpResponse, Http404, HttpResponseNotAllowed, JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.templatetags.static import static

from .utils import is_path_legal, list_subdirs, path_breakdown, aliased_to_abs_path, space_left, pretty_space

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
    return HttpResponse(f"<script>window.location.href = 'mailto:{settings.CONTACT_EMAIL}';</script>")


def share(request:HttpRequest):
    """Allows the admin to create a new share"""
    if not request.user.is_staff:
        log.warning(f"Tried illegal access to share page. Headers: {request.headers}")
        raise PermissionDenied()
    
    if request.method == "GET":
        #TODO: dynamic space check
        bytes_upload_space = space_left(settings.BASE_STORAGE_PATH)
        pretty_upload_space = pretty_space(bytes_upload_space)
        return render(request, "ouitransfer/admin_share.html",
                      {"ALLOWED_ROOTS": [f"{cpl[1]}/" if cpl[1] is not None else cpl[0] for cpl in settings.ALLOWED_STORAGE_ROOTS],
                       "bytes_upload_space": bytes_upload_space, "pretty_upload_space": pretty_upload_space,
                       "upload_chunk_size": settings.UPLOAD_CHUNK_SIZE})
    
    else:
        log.warning(f"Invalid request method for share: {request.method}")
        return HttpResponseNotAllowed(["GET"])


def start_share(request:HttpRequest):
    """Validates the share form data and creates a ShareModel, returning its id for the upload"""
    if not request.user.is_staff:
        log.warning(f"Tried illegal share start. Headers: {request.headers}")
        raise PermissionDenied()
    if request.method != "POST":
        log.warning(f"Invalid request method for share start: {request.method}")
        return HttpResponseNotAllowed(["POST"])
    print(f"start_share -> POST:{request.POST}")
    # TODO: validate public/email/message/expire/delay/delay-unit fields
    # TODO: rebuild and validate the storage path from path-0, path-1... fields, check against is_path_legal
    # TODO: create and save a ShareModel with the validated data
    # TODO: return JsonResponse({"share_id": str(share.id)})
    return JsonResponse({"share_id": "TODO"})


def start_file_share(request:HttpRequest):
    """Registers a new file under a share and returns its id for chunk uploads"""
    if not request.user.is_staff:
        log.warning(f"Tried illegal share file start. Headers: {request.headers}")
        raise PermissionDenied()
    if request.method != "POST":
        log.warning(f"Invalid request method for share file start: {request.method}")
        return HttpResponseNotAllowed(["POST"])
    share_id = request.POST.get("share_id")
    filename = request.POST.get("filename")
    file_size = request.POST.get("file_size")
    print(f"start_file_share -> share_id: {share_id} | filename: {filename} | file_size: {file_size}")
    # TODO: fetch the ShareModel by share_id, 404 if missing
    # TODO: check remaining space (enough_space) against file_size
    # TODO: create and save a FileModel(share=share, filename=filename, file_size=file_size)
    # TODO: return JsonResponse({"file_id": str(file.id)})
    return JsonResponse({"file_id": "TODO"})


def upload_chunk_share(request:HttpRequest):
    """Receives one chunk and writes it to temp storage, keyed by file id and chunk index"""
    if not request.user.is_staff:
        log.warning(f"Tried illegal share chunk upload. Headers: {request.headers}")
        raise PermissionDenied()
    if request.method != "POST":
        log.warning(f"Invalid request method for share chunk upload: {request.method}")
        return HttpResponseNotAllowed(["POST"])
    file_id = request.POST.get("file_id")
    chunk_index = request.POST.get("chunk_index")
    total_chunks = request.POST.get("total_chunks")
    chunk = request.FILES.get("chunk")
    print(f"upload_chunk_share -> file_id: {file_id} | chunk_index: {chunk_index} | total_chunks: {total_chunks}")
    # TODO: fetch the FileModel by file_id, 404 if missing
    # TODO: write chunk to e.g. <tmp_dir>/<file_id>/<chunk_index>.part
    # TODO: update file.last_chunk_date, save
    return JsonResponse({"ok": True})


def finish_file_share(request:HttpRequest):
    """Assembles all received chunks into the final file and verifies its integrity"""
    if not request.user.is_staff:
        log.warning(f"Tried illegal share file finish. Headers: {request.headers}")
        raise PermissionDenied()
    if request.method != "POST":
        log.warning(f"Invalid request method for share file finish: {request.method}")
        return HttpResponseNotAllowed(["POST"])
    file_id = request.POST.get("file_id")
    print(f"finish_file_share -> file_id: {file_id}")
    # TODO: fetch the FileModel by file_id
    # TODO: concatenate the temp chunk parts, in index order, into file.filepath()
    # TODO: verify assembled size == file.file_size; compute and store file.md5
    # TODO: set file.upload_completed = True, save; delete the temp chunk dir
    return JsonResponse({"ok": True})


def finish_share(request:HttpRequest):
    """Finalizes a share once every one of its files has finished uploading"""
    if not request.user.is_staff:
        log.warning(f"Tried illegal share finish. Headers: {request.headers}")
        raise PermissionDenied()
    if request.method != "POST":
        log.warning(f"Invalid request method for share finish: {request.method}")
        return HttpResponseNotAllowed(["POST"])
    share_id = request.POST.get("share_id")
    print(f"finish_share -> share_id: {share_id}")
    # TODO: fetch the ShareModel, verify all related FileModel rows have upload_completed=True
    # TODO: send the notification email if send-email was checked
    return JsonResponse({"ok": True})


def next_dirs(request:HttpRequest):
    """Return a json list of usable directories under the given path, for internal use"""
    if not request.user.is_staff:
        log.warning(f"Tried illegal access to get next directories. Headers: {request.headers}")
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
    #TODO: remove for better handling
    if not request.user.is_staff:
        log.warning(f"Tried getting default directory breakdown illegally. Headers: {request.headers}")
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
