from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from bakery.filesystem import RootedFilesystem, is_root_path, normalize_path


class Command(BaseCommand):
    help = "Empties the build directory"

    def handle(self, *args: object, **kwds: object) -> object:
        filesystem = apps.get_app_config("bakery").filesystem
        build_dir = normalize_path(settings.BUILD_DIR)
        if (
            is_root_path(build_dir)
            and isinstance(filesystem, RootedFilesystem)
            and not filesystem.root
        ):
            raise CommandError("BUILD_DIR must not target an unrooted filesystem root.")
        if filesystem.exists(build_dir):
            self.stdout.write("Clearing the build directory\n")
            filesystem.removetree(build_dir)
