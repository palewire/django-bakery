import logging

from django.apps import AppConfig
from django.conf import settings

from bakery.filesystem import RootedFilesystem

logger = logging.getLogger(__name__)


class BakeryConfig(AppConfig):
    name = "bakery"
    verbose_name = "Bakery"
    filesystem_name = getattr(settings, "BAKERY_FILESYSTEM", "osfs:///")
    filesystem = RootedFilesystem.from_url(filesystem_name)
