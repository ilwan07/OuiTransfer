from django.conf import settings
from django.http import HttpRequest, HttpResponse, Http404, HttpResponseNotAllowed, JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib.auth import logout
from django.utils import timezone
from django.shortcuts import render, redirect
from django.templatetags.static import static

from .utils import is_path_legal, list_subdirs, path_breakdown, aliased_to_abs_path, space_left, pretty_space, validate_share_form, get_posint, send_email
from .models import ShareModel, RequestModel, FileModel

import os
from threading import Thread
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
    # validate form and path
    status, frm = validate_share_form(request.POST)
    if not status == "ok":
        return JsonResponse({"ok": False, "error": status})
    ShareObject = ShareModel(public=frm["public"], email=frm["email_address"], email_lang=frm["email_lang"],
                             message=frm["message"], expire_date=frm["expire_date"])
    ShareObject.store_path = str(Path(frm["store_path"]) / str(ShareObject.id))
    ShareObject.save()
    # create folder and info file
    share_dir = Path(frm["store_path"]) / str(ShareObject.id)
    os.mkdir(share_dir)
    open(share_dir/f".ouitransfer_dir_{ShareObject.id}", "w").close()
    return JsonResponse({"ok": True, "share_id": str(ShareObject.id)})


def start_file_share(request:HttpRequest):
    """Registers a new file under a share and returns its id for chunk uploads"""
    #FIXME: clean delete share on error
    if not request.user.is_staff:
        log.warning(f"Tried illegal share file start. Headers: {request.headers}")
        raise PermissionDenied()
    if request.method != "POST":
        log.warning(f"Invalid request method for share file start: {request.method}")
        return HttpResponseNotAllowed(["POST"])
    share_id = request.POST.get("share_id")
    filename = request.POST.get("filename")
    file_size = request.POST.get("file_size")
    if filename is not None:
        filename = filename.replace("/", "")
    
    if None in (share_id, filename, file_size) or filename == "":
        return JsonResponse({"ok": False, "error": "missing_args"})
    if len(filename) > 255:
        return JsonResponse({"ok": False, "error": "filename_too_long"})
    file_size = get_posint(file_size)
    if file_size is None:
        return JsonResponse({"ok": False, "error": "invalid_size"})
    try:
        ShareObject = ShareModel.objects.get(id=share_id)
    except ShareModel.DoesNotExist:
        return JsonResponse({"ok": False, "error": "nonexistant_share"})
    if file_size > space_left(ShareObject.store_path):
        return JsonResponse({"ok": False, "error": "no_space"})
    
    FileObject = FileModel(share=ShareObject, filename=filename, file_size=file_size)
    FileObject.save()
    # preallocate file on disk
    try:
        path = str(FileObject.filepath())
        open(path, "w").close()
        os.truncate(path, FileObject.file_size)
    except Exception as e:
        log.error(f"Error allocating file {FileObject.id}: {e}")
        return JsonResponse({"ok": False, "error": "allocation_error"})
    return JsonResponse({"ok": True, "file_id": str(FileObject.id)})


def upload_chunk_share(request:HttpRequest):
    """Receives one chunk and writes it to the storage using file id and chunk index"""
    if not request.user.is_staff:
        log.warning(f"Tried illegal share chunk upload. Headers: {request.headers}")
        raise PermissionDenied()
    if request.method != "POST":
        log.warning(f"Invalid request method for share chunk upload: {request.method}")
        return HttpResponseNotAllowed(["POST"])
    file_id = request.POST.get("file_id")
    chunk_index = request.POST.get("chunk_index")
    chunk = request.FILES.get("chunk")
    if None in (file_id, chunk_index, chunk):
        return JsonResponse({"ok": False, "error": "missing_args"})
    chunk_index = get_posint(chunk_index)
    if chunk_index is None:
        return JsonResponse({"ok": False, "error": "invalid_index"})
    try:
        FileObject = FileModel.objects.get(id=file_id)
    except FileModel.DoesNotExist:
        return JsonResponse({"ok": False, "error": "nonexistant_file"})
    ShareObject = FileObject.share
    if ShareObject is None:
        return JsonResponse({"ok": False, "error": "not_share_file"})
    if chunk.size > settings.UPLOAD_CHUNK_SIZE:
        return JsonResponse({"ok": False, "error": "chunk_too_large"})
    offset = chunk_index * settings.UPLOAD_CHUNK_SIZE
    if offset + chunk.size > FileObject.file_size:
        log.warning(f"Tried to upload overflow chunk. Headers: {request.headers}")
        return JsonResponse({"ok": False, "error": "write_overflow"})
    chunk_bytes = chunk.read()
    file = os.open(FileObject.filepath().as_posix(), os.O_WRONLY)
    try:
        written = os.pwrite(file, chunk_bytes, offset)
    except Exception as e:
        log.error(f"Error writing chunk to file {FileObject.id}: {e}")
        return JsonResponse({"ok": False, "error": "write_error"})
    finally:
        os.close(file)
    if written < chunk.size:
        log.error(f"Error writing chunk to file {FileObject.id}: did not write every byte")
        return JsonResponse({"ok": False, "error": "write_error"})
    ShareObject.last_chunk_date = timezone.now()
    ShareObject.save()
    return JsonResponse({"ok": True})


def finish_file_share(request:HttpRequest):
    """Finalize file creation"""
    if not request.user.is_staff:
        log.warning(f"Tried illegal share file finish. Headers: {request.headers}")
        raise PermissionDenied()
    if request.method != "POST":
        log.warning(f"Invalid request method for share file finish: {request.method}")
        return HttpResponseNotAllowed(["POST"])
    file_id = request.POST.get("file_id")
    try:
        FileObject = FileModel.objects.get(id=file_id)
    except FileModel.DoesNotExist:
        return JsonResponse({"ok": False, "error": "nonexistant_file"})
    FileObject.upload_completed = True
    FileObject.save()
    
    def md5_thread_func():
        FileObject.compute_md5()
        FileObject.save()
    md5_thread = Thread(target=md5_thread_func)
    md5_thread.daemon = True
    md5_thread.start()  # compute hash in the background, no queue
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
    try:
        ShareObject = ShareModel.objects.get(id=share_id)
    except ShareModel.DoesNotExist:
        return JsonResponse({"ok": False, "error": "nonexistant_share"})
    ShareObject.creation_date = timezone.now()
    ShareObject.upload_completed = True
    ShareObject.save()
    if ShareObject.email is not None:
        send_email(ShareObject.email, "send_share", lang=ShareObject.email_lang, context={"share_id": str(ShareObject.id)})
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
    response = {"dirs": list_subdirs(realpath), "free_space": space_left(realpath)}
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
