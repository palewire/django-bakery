from django.conf import settings
from django.urls import re_path
from bakery.static_views import serve


urlpatterns = [
    re_path(r"^(.*)$", serve, {
        "document_root": settings.BUILD_DIR,
        'show_indexes': True,
        'default': 'index.html'
        }),
]
