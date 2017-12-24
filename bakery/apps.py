import fs
import logging
from django.conf import settings
from django.apps import AppConfig
logger = logging.getLogger(__name__)


class BakeryConfig(AppConfig):
    name = 'bakery'
    verbose_name = "Bakery"

    def ready(self):
        self.filesystem_name = getattr(settings, 'BAKERY_FILESYSTEM', "osfs:///")
        logger.debug("Loading filesystem at {}".format(self.filesystem_name))
        self.filesystem = fs.open_fs(self.filesystem_name)
