from django.conf import settings

def context_values(request):
    """Makes some variables available to templates"""
    return {"CONTACT_EMAIL": settings.CONTACT_EMAIL,
            "GITHUB_REPO": settings.GITHUB_REPO,
            "OWNER": settings.OWNER,
           }
