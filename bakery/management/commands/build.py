import os
import six
import sys
import gzip
import shutil
import logging
import mimetypes
from django.conf import settings
from django.core import management
from bakery import DEFAULT_GZIP_CONTENT_TYPES
from django.core.urlresolvers import get_callable
from django.core.exceptions import ViewDoesNotExist
from django.core.management.base import BaseCommand, CommandError
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Bake out a site as flat files in the build directory'
    build_unconfig_msg = "Build directory unconfigured. Set BUILD_DIR in \
settings.py or provide it with --build-dir"
    views_unconfig_msg = "Bakery views unconfigured. Set BAKERY_VIEWS in \
settings.py or provide a list as arguments."

    def add_arguments(self, parser):
        parser.add_argument('view_list', nargs='*', type=str, default=[])
        parser.add_argument(
            "--build-dir",
            action="store",
            dest="build_dir",
            default='',
            help="Specify the path of the build directory. \
Will use settings.BUILD_DIR by default."
        )
        parser.add_argument(
            "--keep-build-dir",
            action="store_true",
            dest="keep_build_dir",
            default=False,
            help="Skip initializing the build directory before building files."
        )
        parser.add_argument(
            "--skip-static",
            action="store_true",
            dest="skip_static",
            default=False,
            help="Skip collecting the static files when building."
        )
        parser.add_argument(
            "--skip-media",
            action="store_true",
            dest="skip_media",
            default=False,
            help="Skip collecting the media files when building."
        )

    def handle(self, *args, **options):
        """
        Making it happen.
        """
        logger.info("Build started")

        # Set options
        self.set_options(*args, **options)

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

    def set_options(self, *args, **options):
        """
        Configure a few global options before things get going.
        """
        self.verbosity = int(options.get('verbosity', 1))

        # Figure out what build directory to use
        if options.get("build_dir"):
            self.build_dir = options.get("build_dir")
            settings.BUILD_DIR = self.build_dir
        else:
            if not hasattr(settings, 'BUILD_DIR'):
                raise CommandError(self.build_unconfig_msg)
            self.build_dir = settings.BUILD_DIR

        # Figure out what views we'll be using
        if options['view_list']:
            self.view_list = options['view_list']
        else:
            if not hasattr(settings, 'BAKERY_VIEWS'):
                raise CommandError(self.views_unconfig_msg)
            self.view_list = settings.BAKERY_VIEWS

    def init_build_dir(self):
        """
        Clear out the build directory and create a new one.
        """
        # Destroy the build directory, if it exists
        logger.debug("Initializing %s" % self.build_dir)
        if self.verbosity > 1:
            six.print_("Initializing build directory")
        if os.path.exists(self.build_dir):
            shutil.rmtree(self.build_dir)

        # Then recreate it from scratch
        os.makedirs(self.build_dir)

    def build_static(self, *args, **options):
        """
        Builds the static files directory as well as robots.txt and favicon.ico
        """
        logger.debug("Building static directory")
        if self.verbosity > 1:
            six.print_("Building static directory")

        management.call_command(
            "collectstatic",
            interactive=False,
            verbosity=0
        )
        target_dir = os.path.join(self.build_dir, settings.STATIC_URL[1:])

        if os.path.exists(settings.STATIC_ROOT) and settings.STATIC_URL:
            if getattr(settings, 'BAKERY_GZIP', False):
                self.copytree_and_gzip(settings.STATIC_ROOT, target_dir)
            # if gzip isn't enabled, just copy the tree straight over
            else:
                shutil.copytree(settings.STATIC_ROOT, target_dir)

        # If they exist in the static directory, copy the robots.txt
        # and favicon.ico files down to the root so they will work
        # on the live website.
        robot_src = os.path.join(target_dir, 'robots.txt')
        if os.path.exists(robot_src):
            shutil.copy(robot_src, os.path.join(
                settings.BUILD_DIR,
                'robots.txt'
                )
            )

        favicon_src = os.path.join(target_dir, 'favicon.ico')
        if os.path.exists(favicon_src):
            shutil.copy(favicon_src, os.path.join(
                settings.BUILD_DIR,
                'favicon.ico',
                )
            )

    def build_media(self):
        """
        Build the media files.
        """
        logger.debug("Building static directory")
        if self.verbosity > 1:
            six.print_("Building media directory")
        if os.path.exists(settings.MEDIA_ROOT) and settings.MEDIA_URL:
            shutil.copytree(
                settings.MEDIA_ROOT,
                os.path.join(self.build_dir, settings.MEDIA_URL[1:])
            )

    def build_views(self):
        """
        Bake out specified buildable views.
        """
        # Then loop through and run them all
        for view_str in self.view_list:
            logger.debug("Building %s" % view_str)
            if self.verbosity > 1:
                six.print_("Building %s" % view_str)
            try:
                view = get_callable(view_str)
                view().build_method()
            except (TypeError, ViewDoesNotExist, ImportError):
                raise CommandError("View %s does not work." % view_str)

    def copytree_and_gzip(self, source_dir, target_dir):
        """
        Copies the provided source directory to the provided target directory
        and gzips JavaScript, CSS and HTML files along the way.
        """
        # regex to match against. CSS, JS, JSON, HTML files
        gzip_file_match = getattr(
            settings,
            'GZIP_CONTENT_TYPES',
            DEFAULT_GZIP_CONTENT_TYPES
        )

        # Walk through the source directory...
        for (dirpath, dirnames, filenames) in os.walk(source_dir):

            # And for each file...
            for filename in filenames:

                # ... figure out the path to the file...
                og_file = os.path.join(dirpath, filename)

                # And then where we want to copy it to.
                rel_path = os.path.relpath(dirpath, source_dir)
                dest_path = os.path.join(target_dir, rel_path)
                if not os.path.exists(dest_path):
                    os.makedirs(dest_path)

                # determine the mimetype of the file
                content_type = mimetypes.guess_type(og_file)[0]

                # If it isn't a file want to gzip...
                if content_type not in gzip_file_match:
                    # just copy it to the target.
                    shutil.copy(og_file, dest_path)

                # If it is one we want to gzip...
                else:
                    # ... let the world know...
                    logger.debug("Gzipping %s" % filename)
                    if self.verbosity > 1:
                        six.print_("Gzipping %s" % filename)

                    # ... create the new file in the build directory ...
                    f_in = open(og_file, 'rb')
                    f_name = os.path.join(dest_path, filename)

                    # ... copy the file to gzip compressed output ...
                    if float(sys.version[:3]) >= 2.7:
                        f_out = gzip.GzipFile(f_name, 'wb', mtime=0)
                    else:
                        f_out = gzip.GzipFile(f_name, 'wb')

                    # ... and shut it down.
                    f_out.writelines(f_in)
                    f_out.close()
                    f_in.close()
