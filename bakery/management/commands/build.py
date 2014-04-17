import os
import re
import six
import shutil
from django.conf import settings
from optparse import make_option
from django.core import management
from django.core.urlresolvers import get_callable
from django.core.exceptions import ViewDoesNotExist
from django.core.management.base import BaseCommand, CommandError


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

    def handle(self, *args, **options):
        """
        Making it happen.
        """
        self.verbosity = int(options.get('verbosity'))

        # Figure out what build directory to use
        if options.get("build_dir"):
            self.build_dir = options.get("build_dir")
            settings.BUILD_DIR = self.build_dir
        else:
            if not hasattr(settings, 'BUILD_DIR'):
                raise CommandError(self.build_unconfig_msg)
            self.build_dir = settings.BUILD_DIR

        # Destroy the build directory, if it exists
        if self.verbosity > 1:
            six.print_("Creating build directory")
        if os.path.exists(self.build_dir):
            shutil.rmtree(self.build_dir)

        # Then recreate it from scratch
        os.makedirs(self.build_dir)

        # Build up static files
        if not options.get("skip_static"):
            if self.verbosity > 1:
                six.print_("Creating static directory")
            management.call_command(
                "collectstatic",
                interactive=False,
                verbosity=0
            )
            target_dir = os.path.join(self.build_dir, settings.STATIC_URL[1:])
        
            if os.path.exists(settings.STATIC_ROOT) and settings.STATIC_URL:
                if getattr(settings, 'BAKERY_GZIP', False):
                    for (dirpath, dirnames, filenames) in os.walk(settings.STATIC_ROOT):
                        # regex to match against. CSS, JS, JSON files
                        pattern = re.compile('(\.css|\.js|\.json)$')
                        for filename in filenames:
                            # reference to the original file
                            og_file = os.path.join(dirpath, filename)
                            # get the relative path that we want to copy into
                            rel_path = os.path.relpath(dirpath, settings.STATIC_ROOT)
                            new_file = os.path.join(target_dir, rel_path, filename)
                            # run the regex match
                            m = pattern.search(filename)
                            if m:
                                print "gzipping %s" % filename
                                # create the new path in the build directory
                                f_in = open(og_file, 'rb')
                                # copy the file to gzip compressed output
                                f_out = gzip.open(new_file, 'wb', mtime=0)
                                f_out.writelines(f_in)
                                f_out.close()
                                f_in.close()
                            # otherwise, just copy the file
                            else:
                                shutil.copy(og_file, new_file)
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
            if self.verbosity > 1:
                six.print_("Building %s" % view_str)
            try:
                view = get_callable(view_str)
                view().build_method()
            except (TypeError, ViewDoesNotExist):
                raise CommandError("View %s does not work." % view_str)
