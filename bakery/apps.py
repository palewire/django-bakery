import fs
import logging
from django.conf import settings
from django.apps import AppConfig
logger = logging.getLogger(__name__)


class BakeryConfig(AppConfig):
    name = 'bakery'
    verbose_name = "Bakery"
    filesystem_name = getattr(settings, 'BAKERY_FILESYSTEM', "osfs:///")
    logger.debug("Loading filesystem at {}".format(filesystem_name))
    filesystem = fs.open_fs(self.filesystem_name)
    
    def ready(self):
        pass
