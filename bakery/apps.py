from django.apps import AppConfig
from django.conf import settings


class BakeryConfig(AppConfig):
    name = 'bakery'
    verbose_name = "Bakery"

    def ready(self):
        pass
