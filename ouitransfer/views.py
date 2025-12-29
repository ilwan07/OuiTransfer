from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.contrib.auth import logout
from django.shortcuts import render, redirect


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
