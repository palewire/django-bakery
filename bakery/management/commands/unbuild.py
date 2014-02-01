import os
import shutil
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Empties the build directory"

    def handle(self, *args, **kwds):
        if os.path.exists(settings.BUILD_DIR):
            self.stdout.write("Clearing the build directory\n")
            shutil.rmtree(settings.BUILD_DIR)
