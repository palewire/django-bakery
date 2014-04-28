import os
import re
import six
import sys
import gzip
import shutil
import logging
from django.conf import settings
from optparse import make_option
from django.core import management
from django.core.urlresolvers import get_callable
from django.core.exceptions import ViewDoesNotExist
from django.core.management.base import BaseCommand, CommandError
logger = logging.getLogger(__name__)


custom_options = (
    make_option(
        "--build-dir",
        action="store",
        dest="build_dir",
        default='',
        help="Specify the path of the build directory. \
Will use settings.BUILD_DIR by default."
    ),
    make_option(
        "--skip-static",
        action="store_true",
        dest="skip_static",
        default=False,
        help="Skip collecting the static files when building."
    ),
    make_option(
        "--skip-media",
        action="store_true",
        dest="skip_media",
        default=False,
        help="Skip collecting the media files when building."
    ),
)


class Command(BaseCommand):
    help = 'Bake out a site as flat files in the build directory'
    option_list = BaseCommand.option_list + custom_options
    build_unconfig_msg = "Build directory unconfigured. Set BUILD_DIR in \
settings.py or provide it with --build-dir"
    views_unconfig_msg = "Bakery views unconfigured. Set BAKERY_VIEWS in \
settings.py or provide a list as arguments."

    def copytree_and_gzip(self, source_dir, target_dir):
        """
        Copies the provided source directory to the provided target directory
        and gzips JavaScript, CSS and HTML files along the way.
        """
        # regex to match against. CSS, JS, JSON, HTML files
        gzip_file_match = getattr(
            settings,
            'GZIP_FILE_MATCH',
            '(\.html|\.xml|\.css|\.js|\.json)$'
        )
        pattern = re.compile(gzip_file_match)

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

                # If it isn't a file want to gzip...
                if not pattern.search(filename):
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

    def handle(self, *args, **options):
        """
        Making it happen.
        """
        self.verbosity = int(options.get('verbosity'))
        logger.info("Build started")

        # Figure out what build directory to use
        if options.get("build_dir"):
            self.build_dir = options.get("build_dir")
            settings.BUILD_DIR = self.build_dir
        else:
            if not hasattr(settings, 'BUILD_DIR'):
                raise CommandError(self.build_unconfig_msg)
            self.build_dir = settings.BUILD_DIR

        # Destroy the build directory, if it exists
        logger.debug("Creating %s" % self.build_dir)
        if self.verbosity > 1:
            six.print_("Creating build directory")
        if os.path.exists(self.build_dir):
            shutil.rmtree(self.build_dir)

        # Then recreate it from scratch
        os.makedirs(self.build_dir)

        # Build up static files
        if not options.get("skip_static"):
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
            favicon_src = os.path.join(target_dir, 'favicon.ico')
            if os.path.exists(robot_src):
                shutil.copy(robot_src, os.path.join(
                    settings.BUILD_DIR,
                    'robots.txt'
                    )
                )
            if os.path.exists(favicon_src):
                shutil.copy(favicon_src, os.path.join(
                    settings.BUILD_DIR,
                    'favicon.ico',
                    )
                )

        # Build the media directory
        if not options.get("skip_media"):
            logger.debug("Building static directory")
            if self.verbosity > 1:
                six.print_("Building media directory")
            if os.path.exists(settings.MEDIA_ROOT) and settings.MEDIA_URL:
                shutil.copytree(
                    settings.MEDIA_ROOT,
                    os.path.join(self.build_dir, settings.MEDIA_URL[1:])
                )

        # Figure out what views we'll be using
        if args:
            view_list = args
        else:
            if not hasattr(settings, 'BAKERY_VIEWS'):
                raise CommandError(self.views_unconfig_msg)
            view_list = settings.BAKERY_VIEWS

        # Then loop through and run them all
        for view_str in view_list:
            logger.debug("Building %s" % view_str)
            if self.verbosity > 1:
                six.print_("Building %s" % view_str)
            try:
                view = get_callable(view_str)
                view().build_method()
            except (TypeError, ViewDoesNotExist):
                raise CommandError("View %s does not work." % view_str)
