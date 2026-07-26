import logging
import fsspec
from django.conf import settings
from django.apps import AppConfig
logger = logging.getLogger(__name__)

# Map legacy PyFilesystem2 URL schemes to their fsspec equivalents so that
# existing BAKERY_FILESYSTEM settings keep working after the migration.
LEGACY_SCHEME_MAP = {
    "osfs": "file",
    "mem": "memory",
}


def open_filesystem(filesystem_name):
    """
    Return an fsspec filesystem for the provided BAKERY_FILESYSTEM value.

    Legacy PyFilesystem2 schemes (``osfs://``, ``mem://``) are translated to
    their fsspec equivalents (``file``, ``memory``). Any other URL is handed
    straight to fsspec, so ``s3://`` (via s3fs), ``gcs://`` (via gcsfs) and
    friends work as long as the matching backend is installed.
    """
    protocol = filesystem_name.split("://", 1)[0] if "://" in filesystem_name else filesystem_name
    if protocol in LEGACY_SCHEME_MAP:
        return fsspec.filesystem(LEGACY_SCHEME_MAP[protocol])
    filesystem, _ = fsspec.core.url_to_fs(filesystem_name)
    return filesystem


class BakeryConfig(AppConfig):
    name = 'bakery'
    verbose_name = "Bakery"
    filesystem_name = getattr(settings, 'BAKERY_FILESYSTEM', "osfs:///")
    filesystem = open_filesystem(filesystem_name)
