import logging
import warnings
import fsspec
from django.conf import settings
from django.apps import AppConfig
from bakery import BakeryDeprecationWarning
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

    Legacy PyFilesystem2 schemes (``osfs://``, ``mem://``) are still accepted
    and translated to their fsspec equivalents (``file``, ``memory``), but they
    are deprecated and raise a ``BakeryDeprecationWarning``. Any other URL is
    handed straight to fsspec, so ``s3://`` (via s3fs), ``gcs://`` (via gcsfs)
    and friends work as long as the matching backend is installed.
    """
    protocol = filesystem_name.split("://", 1)[0] if "://" in filesystem_name else filesystem_name
    if protocol in LEGACY_SCHEME_MAP:
        replacement = LEGACY_SCHEME_MAP[protocol]
        warnings.warn(
            "The '{0}://' BAKERY_FILESYSTEM scheme is a deprecated PyFilesystem2 "
            "alias and will be removed in a future release. Use '{1}://' instead.".format(
                protocol, replacement
            ),
            BakeryDeprecationWarning,
            stacklevel=2,
        )
        return fsspec.filesystem(replacement)
    filesystem, _ = fsspec.core.url_to_fs(filesystem_name)
    return filesystem


class BakeryConfig(AppConfig):
    name = 'bakery'
    verbose_name = "Bakery"
    filesystem_name = getattr(settings, 'BAKERY_FILESYSTEM', "file://")
    filesystem = open_filesystem(filesystem_name)
