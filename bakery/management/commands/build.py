#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Env
import os
import sys
import six

# Files
import gzip
import mimetypes
from bakery import DEFAULT_GZIP_CONTENT_TYPES

# Filesystem
from fs import path
from fs import copy
from django.utils.encoding import smart_text

# Pooling
import multiprocessing
from multiprocessing.pool import ThreadPool

# Django tricks
from django.apps import apps
from django.conf import settings
from django.core import management
try:
    from django.core.urlresolvers import get_callable
except ImportError:
    # Starting with Django 2.0, django.core.urlresolvers does not exist anymore
    from django.urls import get_callable
from django.core.management.base import BaseCommand, CommandError

# Logging
import logging
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
        self.app = apps.get_app_config("bakery")
        self.fs = self.app.filesystem
        self.fs_name = self.app.filesystem_name

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

        # Are we pooling?
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

        # Set the target directory inside the filesystem.
        target_dir = path.join(
            self.build_dir,
            settings.STATIC_URL.lstrip('/')
        )
        target_dir = smart_text(target_dir)

        if os.path.exists(self.static_root) and settings.STATIC_URL:
            if getattr(settings, 'BAKERY_GZIP', False):
                self.copytree_and_gzip(self.static_root, target_dir)
            # if gzip isn't enabled, just copy the tree straight over
            else:
                logger.debug("Copying {}{} to {}{}".format("osfs://", self.static_root, self.fs_name, target_dir))
                copy.copy_dir("osfs:///", self.static_root, self.fs, target_dir)

        # If they exist in the static directory, copy the robots.txt
        # and favicon.ico files down to the root so they will work
        # on the live website.
        robots_src = path.join(target_dir, 'robots.txt')
        if self.fs.exists(robots_src):
            robots_target = path.join(self.build_dir, 'robots.txt')
            logger.debug("Copying {}{} to {}{}".format(self.fs_name, robots_src, self.fs_name, robots_target))
            self.fs.copy(robots_src, robots_target)

        favicon_src = path.join(target_dir, 'favicon.ico')
        if self.fs.exists(favicon_src):
            favicon_target = path.join(self.build_dir, 'favicon.ico')
            logger.debug("Copying {}{} to {}{}".format(self.fs_name, favicon_src, self.fs_name, favicon_target))
            self.fs.copy(favicon_src, favicon_target)

    def build_media(self):
        """
        Build the media files.
        """
        logger.debug("Building media directory")
        if self.verbosity > 1:
            self.stdout.write("Building media directory")
        if os.path.exists(self.media_root) and settings.MEDIA_URL:
            target_dir = path.join(self.fs_name, self.build_dir, settings.MEDIA_URL.lstrip('/'))
            logger.debug("Copying {}{} to {}{}".format("osfs://", self.media_root, self.fs_name, target_dir))
            copy.copy_dir("osfs:///", smart_text(self.media_root), self.fs, smart_text(target_dir))

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
        for (dirpath, dirnames, filenames) in os.walk(source_dir):
            for f in filenames:
                # Figure out what is going where
                source_path = os.path.join(dirpath, f)
                rel_path = os.path.relpath(dirpath, source_dir)
                target_path = os.path.join(target_dir, rel_path, f)
                # Add it to our list to build
                build_list.append((source_path, target_path))

        logger.debug("Gzipping {} files".format(len(build_list)))

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
            logger.debug("Copying {}{} to {}{} because its filetype isn't on the whitelist".format(
                "osfs://",
                source_path,
                self.fs_name,
                target_path
            ))
            copy.copy_file("osfs:///", smart_text(source_path), self.fs, smart_text(target_path))

        # # if the file is already gzipped
        elif encoding == 'gzip':
            logger.debug("Copying {}{} to {}{} because it's already gzipped".format(
                "osfs://",
                source_path,
                self.fs_name,
                target_path
            ))
            copy.copy_file("osfs:///", smart_text(source_path), self.fs, smart_text(target_path))

        # If it is one we want to gzip...
        else:
            # ... let the world know ...
            logger.debug("Gzipping {}{} to {}{}".format(
                "osfs://",
                source_path,
                self.fs_name,
                target_path
            ))
            # Open up the source file from the OS
            with open(source_path, 'rb') as source_file:
                # Write GZIP data to an in-memory buffer
                data_buffer = six.BytesIO()
                kwargs = dict(
                    filename=path.basename(target_path),
                    mode='wb',
                    fileobj=data_buffer
                )
                if float(sys.version[:3]) >= 2.7:
                    kwargs['mtime'] = 0
                with gzip.GzipFile(**kwargs) as f:
                    f.write(six.binary_type(source_file.read()))

                # Write that buffer out to the filesystem
                with self.fs.open(smart_text(target_path), 'wb') as outfile:
                    outfile.write(data_buffer.getvalue())
                    outfile.close()
