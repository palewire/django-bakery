from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand

from bakery.filesystem import normalize_path


class Command(BaseCommand):
    help = "Empties the build directory"

    def handle(self, *args: object, **kwds: object) -> object:
        filesystem = apps.get_app_config("bakery").filesystem
        build_dir = normalize_path(settings.BUILD_DIR)
        if filesystem.exists(build_dir):
            self.stdout.write("Clearing the build directory\n")
            filesystem.removetree(build_dir)
