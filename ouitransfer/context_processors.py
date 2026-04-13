from django.conf import settings
from django.utils.translation import get_language

def context_values(request):
    """Makes some variables available to templates"""
    return {"CONTACT_EMAIL": settings.CONTACT_EMAIL,
            "GITHUB_REPO": settings.GITHUB_REPO,
            "OWNER": settings.OWNER,
            "LANGUAGES": settings.LANGUAGES,
            "USER_LANG": get_language(),
            "ALLOWED_STORAGE_ROOTS": settings.ALLOWED_STORAGE_ROOTS,
           }
