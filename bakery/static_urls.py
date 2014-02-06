from django.conf import settings
from django.conf.urls import patterns, url


urlpatterns = patterns(
    "bakery.static_views",
    url(r"^(.*)$", "serve", {
        "document_root": settings.BUILD_DIR,
        'show_indexes': True,
        'default': 'index.html'
        }),
)
