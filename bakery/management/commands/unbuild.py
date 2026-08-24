import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Empties the build directory"

    def handle(self, *args: object, **kwds: object) -> object:
        if Path(settings.BUILD_DIR).exists():
            self.stdout.write("Clearing the build directory\n")
            shutil.rmtree(settings.BUILD_DIR)
