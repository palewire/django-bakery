#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import gzip
import logging
import mimetypes
from fs import path
import multiprocessing
from django.apps import apps
from django.conf import settings
from django.core import management
from multiprocessing.pool import ThreadPool
from bakery import DEFAULT_GZIP_CONTENT_TYPES
try:
    from django.core.urlresolvers import get_callable
except ImportError:
    # Starting with Django 2.0, django.core.urlresolvers does not exist anymore
    from django.urls import get_callable
from django.utils.encoding import smart_text
from django.core.management.base import BaseCommand, CommandError
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Bake out a site as flat files in the build directory'
    build_unconfig_msg = "Build directory unconfigured. Set BUILD_DIR in settings.py or provide it with --build-dir"
    views_unconfig_msg = "Bakery views unconfigured. Set BAKERY_VIEWS in settings.py or provide a list as arguments."
    # regex to match against for gzipping. CSS, JS, JSON, HTML, etc.
    gzip_file_match = getattr(
        settings,
        'GZIP_CONTENT_TYPES',
        DEFAULT_GZIP_CONTENT_TYPES
    )

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
        parser.add_argument(
            "--pooling",
            action="store_true",
            dest="pooling",
            default=False,
            help=("Pool builds to run concurrently rather than running them one by one.")
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

        # Get the datatypes right so fs will be happy
        self.build_dir = smart_text(self.build_dir)
        self.static_root = smart_text(settings.STATIC_ROOT)
        self.media_root = smart_text(settings.MEDIA_ROOT)

        # Connect the BUILD_DIR with our filesystem backend
        self.fs = apps.get_app_config("bakery").filesystem

        # If the build dir doesn't exist make it
        if not self.fs.exists(self.build_dir):
            self.fs.makedirs(self.build_dir)

        # Figure out what views we'll be using
        if options.get('view_list'):
            self.view_list = options['view_list']
        else:
            if not hasattr(settings, 'BAKERY_VIEWS'):
                raise CommandError(self.views_unconfig_msg)
            self.view_list = settings.BAKERY_VIEWS

        self.pooling = options.get('pooling')

    def init_build_dir(self):
        """
        Clear out the build directory and create a new one.
        """
        # Destroy the build directory, if it exists
        logger.debug("Initializing %s" % self.build_dir)
        if self.verbosity > 1:
            self.stdout.write("Initializing build directory")
        if self.fs.exists(self.build_dir):
            self.fs.removetree(self.build_dir)

        # Then recreate it from scratch
        self.fs.makedirs(self.build_dir)

    def build_static(self, *args, **options):
        """
        Builds the static files directory as well as robots.txt and favicon.ico
        """
        logger.debug("Building static directory")
        if self.verbosity > 1:
            self.stdout.write("Building static directory")

        management.call_command(
            "collectstatic",
            interactive=False,
            verbosity=0
        )
        target_dir = path.join(self.build_dir, settings.STATIC_URL.lstrip('/'))

        if self.fs.exists(self.static_root) and settings.STATIC_URL:
            if getattr(settings, 'BAKERY_GZIP', False):
                self.copytree_and_gzip(self.static_root, target_dir)
            # if gzip isn't enabled, just copy the tree straight over
            else:
                self.fs.copydir(self.static_root, target_dir, create=True)

        # If they exist in the static directory, copy the robots.txt
        # and favicon.ico files down to the root so they will work
        # on the live website.
        robot_src = path.join(target_dir, 'robots.txt')
        if self.fs.exists(robot_src):
            self.fs.copy(robot_src, path.join(self.build_dir, 'robots.txt'))

        favicon_src = path.join(target_dir, 'favicon.ico')
        if self.fs.exists(favicon_src):
            self.fs.copy(favicon_src, path.join(self.build_dir, 'favicon.ico'))

    def build_media(self):
        """
        Build the media files.
        """
        logger.debug("Building media directory")
        if self.verbosity > 1:
            self.stdout.write("Building media directory")
        if self.fs.exists(self.media_root) and settings.MEDIA_URL:
            self.fs.copydir(
                self.media_root,
                path.join(self.build_dir, settings.MEDIA_URL.lstrip('/')),
                create=True,
            )

    def get_view_instance(self, view):
        """
        Given a view class, get an instance of it.
        """
        return view()

    def build_views(self):
        """
        Bake out specified buildable views.
        """
        # Then loop through and run them all
        for view_str in self.view_list:
            logger.debug("Building %s" % view_str)
            if self.verbosity > 1:
                self.stdout.write("Building %s" % view_str)
            view = get_callable(view_str)
            self.get_view_instance(view).build_method()

    def copytree_and_gzip(self, source_dir, target_dir):
        """
        Copies the provided source directory to the provided target directory.

        Gzips JavaScript, CSS and HTML and other files along the way.
        """
        # Figure out what we're building...
        build_list = []
        # Walk through the source directory...
        for (dirpath, dirnames, filenames) in self.fs.walk(source_dir):
            for f in filenames:
                # Figure out what is going where
                source_path = path.join(dirpath, f.name)
                rel_path = os.path.relpath(dirpath, source_dir)
                target_path = path.join(target_dir, rel_path, f.name)
                # Add it to our list to build
                build_list.append((source_path, target_path))

        # Build em all
        if not getattr(self, 'pooling', False):
            [self.copyfile_and_gzip(*u) for u in build_list]
        else:
            cpu_count = multiprocessing.cpu_count()
            logger.debug("Pooling build on {} CPUs".format(cpu_count))
            pool = ThreadPool(processes=cpu_count)
            pool.map(self.pooled_copyfile_and_gzip, build_list)

    def pooled_copyfile_and_gzip(self, payload):
        """
        A passthrough for our ThreadPool because it can't take two arguments.

        So all we're doing here is split the list into args for the real function.
        """
        self.copyfile_and_gzip(*payload)

    def copyfile_and_gzip(self, source_path, target_path):
        """
        Copies the provided file to the provided target directory.

        Gzips JavaScript, CSS and HTML and other files along the way.
        """
        # And then where we want to copy it to.
        target_dir = path.dirname(target_path)
        if not self.fs.exists(target_dir):
            try:
                self.fs.makedirs(target_dir)
            except OSError:
                pass

        # determine the mimetype of the file
        guess = mimetypes.guess_type(source_path)
        content_type = guess[0]
        encoding = guess[1]

        # If it isn't a file want to gzip...
        if content_type not in self.gzip_file_match:
            # just copy it to the target.
            logger.debug("Not gzipping %s" % source_path)
            self.fs.copy(source_path, target_path, overwrite=True)

        # # if the file is already gzipped
        elif encoding == 'gzip':
            logger.debug("Not gzipping %s" % source_path)
            self.fs.copy(source_path, target_path, overwrite=True)

        # If it is one we want to gzip...
        else:
            # ... let the world know ...
            logger.debug("Gzipping %s" % target_path)
            if self.verbosity > 1:
                self.stdout.write("Gzipping %s" % target_path)

            # ... create the new file in the build directory ...
            with self.fs.open(source_path, 'rb') as source_file:
                # ... copy the file to gzip compressed output ...
                if float(sys.version[:3]) >= 2.7:
                    target_file = gzip.GzipFile(target_path, 'wb', mtime=0)
                else:
                    target_file = gzip.GzipFile(target_path, 'wb')

                # ... and shut it down.
                target_file.writelines(source_file)
                target_file.close()
