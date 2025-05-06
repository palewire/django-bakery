import logging
from pathlib import Path

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class BakeryConfig(AppConfig):
    name = "bakery"
    verbose_name = "Bakery"
    filesystem_path = Path(getattr(settings, "BAKERY_FILESYSTEM_PATH", "/"))
