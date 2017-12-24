import fs
from django.conf import settings
from django.apps import AppConfig


class BakeryConfig(AppConfig):
    name = 'bakery'
    verbose_name = "Bakery"

    def ready(self):
        self.filesystem = fs.open_fs(getattr(settings, 'BAKERY_FILESYSTEM', "osfs:///"))
