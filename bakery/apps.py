import logging

import fs
from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class BakeryConfig(AppConfig):
    name = "bakery"
    verbose_name = "Bakery"
    filesystem_name = getattr(settings, "BAKERY_FILESYSTEM", "osfs:///")
    filesystem = fs.open_fs(filesystem_name)
