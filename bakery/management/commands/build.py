import gzip
import io
import logging
import mimetypes
import multiprocessing
import os
import posixpath
import shutil
from argparse import ArgumentParser
from collections.abc import Callable, Mapping
from multiprocessing.pool import ThreadPool
from pathlib import Path
from typing import Protocol, TypeAlias, cast

from django.apps import apps
from django.conf import settings
from django.core import management
from django.core.management.base import BaseCommand, CommandError
from django.urls import get_callable
from django.utils.encoding import smart_str

from bakery import DEFAULT_GZIP_CONTENT_TYPES
from bakery.filesystem import RootedFilesystem, join_path, normalize_path

logger = logging.getLogger(__name__)

CommandOptions: TypeAlias = Mapping[str, object]
BuildPayload: TypeAlias = tuple[str, str]


class BuildableView(Protocol):
    def build_method(self) -> object: ...


class Command(BaseCommand):
    help = "Bake out a site as flat files in the build directory"
    build_unconfig_msg = "Build directory unconfigured. Set BUILD_DIR in settings.py or provide it with --build-dir"
    views_unconfig_msg = "Bakery views unconfigured. Set BAKERY_VIEWS in settings.py or provide a list as arguments."
    # regex to match against for gzipping. CSS, JS, JSON, HTML, etc.
    gzip_file_match = getattr(
        settings, "GZIP_CONTENT_TYPES", DEFAULT_GZIP_CONTENT_TYPES
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("view_list", nargs="*", type=str, default=[])
        parser.add_argument(
            "--build-dir",
            action="store",
            dest="build_dir",
            default="",
            help="Specify the path of the build directory. \
Will use settings.BUILD_DIR by default.",
        )
        parser.add_argument(
            "--keep-build-dir",
            action="store_true",
            dest="keep_build_dir",
            default=False,
            help="Skip initializing the build directory before building files.",
        )
        parser.add_argument(
            "--skip-static",
            action="store_true",
            dest="skip_static",
            default=False,
            help="Skip collecting the static files when building.",
        )
        parser.add_argument(
            "--skip-media",
            action="store_true",
            dest="skip_media",
            default=False,
            help="Skip collecting the media files when building.",
        )
        parser.add_argument(
            "--pooling",
            action="store_true",
            dest="pooling",
            default=False,
            help=(
                "Pool builds to run concurrently rather than running them one by one."
            ),
        )

    def handle(self, *args: object, **options: object) -> None:
        """
        Making it happen.
        """
        logger.info("Build started")

        # Set options
        self.set_options(*args, options=cast("CommandOptions", options))

        # Get the build directory ready
        if not options.get("keep_build_dir"):
            self.init_build_dir()

        # Build up static files
        if not options.get("skip_static"):
            self.build_static()

        # Build the media directory
        if not options.get("skip_media"):
            self.build_media()

        # Build views
        self.build_views()

        # Close out
        logger.info("Build finished")

    def set_options(self, *args: object, options: CommandOptions) -> None:
        """
        Configure a few global options before things get going.
        """
        self.verbosity = int(cast("int | str", options.get("verbosity", 1)))

        # Figure out what build directory to use
        build_dir = cast("str", options.get("build_dir"))
        if build_dir:
            self.build_dir = build_dir
            settings.BUILD_DIR = self.build_dir
        else:
            if not hasattr(settings, "BUILD_DIR"):
                raise CommandError(self.build_unconfig_msg)
            self.build_dir = settings.BUILD_DIR

        self.build_dir = normalize_path(smart_str(self.build_dir))
        self.static_root = smart_str(settings.STATIC_ROOT)
        self.media_root = smart_str(settings.MEDIA_ROOT)

        # Connect the BUILD_DIR with our filesystem backend
        self.app = apps.get_app_config("bakery")
        self.fs = self.app.filesystem
        self.fs_name = self.app.filesystem_name
        if (
            self.build_dir == "."
            and isinstance(self.fs, RootedFilesystem)
            and not self.fs.root
        ):
            raise CommandError("BUILD_DIR must not target an unrooted filesystem root.")

        # If the build dir doesn't exist make it
        if not self.fs.exists(self.build_dir):
            self.fs.makedirs(self.build_dir)

        # Figure out what views we'll be using
        view_list = cast("list[str]", options.get("view_list"))
        if view_list:
            self.view_list = view_list
        else:
            if not hasattr(settings, "BAKERY_VIEWS"):
                raise CommandError(self.views_unconfig_msg)
            self.view_list = settings.BAKERY_VIEWS

        # Are we pooling?
        self.pooling = cast("bool", options.get("pooling"))

    def init_build_dir(self) -> None:
        """
        Clear out the build directory and create a new one.
        """
        # Destroy the build directory, if it exists
        logger.debug("Initializing %s", self.build_dir)
        if self.verbosity > 1:
            self.stdout.write("Initializing build directory")
        if self.fs.exists(self.build_dir):
            self.fs.removetree(self.build_dir)
        # Then recreate it from scratch
        self.fs.makedirs(self.build_dir)

    def build_static(self, *args: object, **options: object) -> None:
        """
        Builds the static files directory as well as robots.txt and favicon.ico
        """
        logger.debug("Building static directory")
        if self.verbosity > 1:
            self.stdout.write("Building static directory")
        management.call_command("collectstatic", interactive=False, verbosity=0)

        # Set the target directory inside the filesystem.
        target_dir = join_path(self.build_dir, settings.STATIC_URL.lstrip("/"))

        if Path(self.static_root).exists() and settings.STATIC_URL:
            if getattr(settings, "BAKERY_GZIP", False):
                self.copytree_and_gzip(self.static_root, target_dir)
            # if gzip isn't enabled, just copy the tree straight over
            else:
                logger.debug(
                    "Copying osfs://%s to %s%s",
                    self.static_root,
                    self.fs_name,
                    target_dir,
                )
                self.copytree(self.static_root, target_dir)

        # If they exist in the static directory, copy the robots.txt
        # and favicon.ico files down to the root so they will work
        # on the live website.
        robots_src = join_path(target_dir, "robots.txt")
        if self.fs.exists(robots_src):
            robots_target = join_path(self.build_dir, "robots.txt")
            logger.debug(
                "Copying %s%s to %s%s",
                self.fs_name,
                robots_src,
                self.fs_name,
                robots_target,
            )
            self.fs.copy(robots_src, robots_target)

        favicon_src = join_path(target_dir, "favicon.ico")
        if self.fs.exists(favicon_src):
            favicon_target = join_path(self.build_dir, "favicon.ico")
            logger.debug(
                "Copying %s%s to %s%s",
                self.fs_name,
                favicon_src,
                self.fs_name,
                favicon_target,
            )
            self.fs.copy(favicon_src, favicon_target)

    def build_media(self) -> None:
        """
        Build the media files.
        """
        logger.debug("Building media directory")
        if self.verbosity > 1:
            self.stdout.write("Building media directory")
        if Path(self.media_root).exists() and settings.MEDIA_URL:
            target_dir = join_path(self.build_dir, settings.MEDIA_URL.lstrip("/"))
            logger.debug(
                "Copying osfs://%s to %s%s",
                self.media_root,
                self.fs_name,
                target_dir,
            )
            self.copytree(self.media_root, target_dir)

    def get_view_instance(self, view: Callable[[], BuildableView]) -> BuildableView:
        """
        Given a view class, get an instance of it.
        """
        return view()

    def build_views(self) -> None:
        """
        Bake out specified buildable views.
        """
        # Then loop through and run them all
        for view_str in self.view_list:
            logger.debug("Building %s", view_str)
            if self.verbosity > 1:
                self.stdout.write(f"Building {view_str}")
            view = cast("Callable[[], BuildableView]", get_callable(view_str))
            self.get_view_instance(view).build_method()

    def copytree_and_gzip(self, source_dir: str, target_dir: str) -> None:
        """
        Copies the provided source directory to the provided target directory.

        Gzips JavaScript, CSS and HTML and other files along the way.
        """
        # Figure out what we're building...
        build_list: list[BuildPayload] = []
        # Walk through the source directory...
        for dirpath, _dirnames, filenames in os.walk(source_dir):
            for f in filenames:
                # Figure out what is going where
                source_path = str(Path(dirpath) / f)
                rel_path = os.path.relpath(dirpath, source_dir)
                target_path = join_path(target_dir, rel_path, f)
                # Add it to our list to build
                build_list.append((source_path, target_path))

        logger.debug("Gzipping %s files", len(build_list))

        # Build em all
        if not getattr(self, "pooling", False):
            for build in build_list:
                self.copyfile_and_gzip(*build)
        else:
            cpu_count = multiprocessing.cpu_count()
            logger.debug("Pooling build on %s CPUs", cpu_count)
            pool = ThreadPool(processes=cpu_count)
            pool.map(self.pooled_copyfile_and_gzip, build_list)

    def pooled_copyfile_and_gzip(self, payload: BuildPayload) -> None:
        """
        A passthrough for our ThreadPool because it can't take two arguments.

        So all we're doing here is split the list into args for the real function.
        """
        self.copyfile_and_gzip(*payload)

    def copyfile_and_gzip(self, source_path: str, target_path: str) -> None:
        """
        Copies the provided file to the provided target directory.

        Gzips JavaScript, CSS and HTML and other files along the way.
        """
        # And then where we want to copy it to.
        target_dir = posixpath.dirname(target_path)
        if not self.fs.exists(target_dir):
            self.fs.makedirs(target_dir)

        # determine the mimetype of the file
        guess = mimetypes.guess_type(source_path)
        content_type = guess[0]
        encoding = guess[1]

        # If it isn't a file want to gzip...
        if content_type not in self.gzip_file_match:
            # just copy it to the target.
            logger.debug(
                "Copying osfs://%s to %s%s because its filetype isn't on the whitelist",
                source_path,
                self.fs_name,
                target_path,
            )
            self.copy_local_file(source_path, target_path)

        # # if the file is already gzipped
        elif encoding == "gzip":
            logger.debug(
                "Copying osfs://%s to %s%s because it's already gzipped",
                source_path,
                self.fs_name,
                target_path,
            )
            self.copy_local_file(source_path, target_path)

        # If it is one we want to gzip...
        else:
            # ... let the world know ...
            logger.debug(
                "Gzipping osfs://%s to %s%s",
                source_path,
                self.fs_name,
                target_path,
            )
            # Open up the source file from the OS
            with Path(source_path).open("rb") as source_file:
                # Write GZIP data to an in-memory buffer
                data_buffer = io.BytesIO()
                with gzip.GzipFile(
                    filename=posixpath.basename(target_path),
                    mode="wb",
                    fileobj=data_buffer,
                    mtime=0,
                ) as f:
                    f.write(source_file.read())

                # Write that buffer out to the filesystem
                with self.fs.open(smart_str(target_path), "wb") as outfile:
                    outfile.write(data_buffer.getvalue())

    def copytree(self, source_dir: str, target_dir: str) -> None:
        """Copy a local directory into the configured output backend."""
        for dirpath, _dirnames, filenames in os.walk(source_dir):
            for filename in filenames:
                source_path = str(Path(dirpath) / filename)
                relative_path = os.path.relpath(source_path, source_dir)
                self.copy_local_file(source_path, join_path(target_dir, relative_path))

    def copy_local_file(self, source_path: str, target_path: str) -> None:
        """Copy one local file into the configured output backend."""
        target_dir = posixpath.dirname(target_path)
        if target_dir and not self.fs.exists(target_dir):
            self.fs.makedirs(target_dir)
        with (
            Path(source_path).open("rb") as source,
            self.fs.open(target_path, "wb") as target,
        ):
            shutil.copyfileobj(source, target)
