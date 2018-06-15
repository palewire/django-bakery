#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views that inherit from Django's class-based generic views and add methods
for building flat files.
"""
from __future__ import unicode_literals
import os
import six
import sys
import gzip
import logging
import mimetypes
from fs import path
from django.apps import apps
from django.conf import settings
from django.utils.encoding import smart_text
from bakery import DEFAULT_GZIP_CONTENT_TYPES
from django.test.client import RequestFactory
from bakery.management.commands import get_s3_client
from django.views.generic import RedirectView, TemplateView
try:
    from django.core.urlresolvers import reverse, NoReverseMatch
except ImportError:  # Starting with Django 2.0, django.core.urlresolvers does not exist anymore
    from django.urls import reverse, NoReverseMatch
logger = logging.getLogger(__name__)


class BuildableMixin(object):
    """
    Common methods we will use in buildable views.
    """
    fs_name = apps.get_app_config("bakery").filesystem_name
    fs = apps.get_app_config("bakery").filesystem

    def create_request(self, path):
        """
        Returns a GET request object for use when building views.

        If inheriting views require additional request attributes
        (e.g. user, site), override this method and define those
        attributes on the returned object.
        """
        return RequestFactory().get(path)

    def get_content(self):
        """
        How to render the HTML or other content for the page.

        If you choose to render using something other than a Django template,
        like HttpResponse for instance, you will want to override this.
        """
        return self.get(self.request).render().content

    def prep_directory(self, target_dir):
        """
        Prepares a new directory to store the file at the provided path, if needed.
        """
        dirname = path.dirname(target_dir)
        if dirname:
            dirname = path.join(settings.BUILD_DIR, dirname)
            if not self.fs.exists(dirname):
                logger.debug("Creating directory at {}{}".format(self.fs_name, dirname))
                self.fs.makedirs(dirname)

    def build_file(self, path, html):
        if self.is_gzippable(path):
            self.gzip_file(path, html)
        else:
            self.write_file(path, html)

    def write_file(self, target_path, html):
        """
        Writes out the provided HTML to the provided path.
        """
        logger.debug("Building to {}{}".format(self.fs_name, target_path))
        with self.fs.open(smart_text(target_path), 'wb') as outfile:
            outfile.write(six.binary_type(html))
            outfile.close()

    def is_gzippable(self, path):
        """
        Returns a boolean indicating if the provided file path is a candidate
        for gzipping.
        """
        # First check if gzipping is allowed by the global setting
        if not getattr(settings, 'BAKERY_GZIP', False):
            return False
        # Then check if the content type of this particular file is gzippable
        whitelist = getattr(
            settings,
            'GZIP_CONTENT_TYPES',
            DEFAULT_GZIP_CONTENT_TYPES
        )
        return mimetypes.guess_type(path)[0] in whitelist

    def gzip_file(self, target_path, html):
        """
        Zips up the provided HTML as a companion for the provided path.

        Intended to take advantage of the peculiarities of
        Amazon S3's GZIP service.

        mtime, an option that writes a timestamp to the output file
        is set to 0, to avoid having s3cmd do unnecessary uploads because
        of differences in the timestamp
        """
        logger.debug("Gzipping to {}{}".format(self.fs_name, target_path))

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
            f.write(six.binary_type(html))

        # Write that buffer out to the filesystem
        with self.fs.open(smart_text(target_path), 'wb') as outfile:
            outfile.write(data_buffer.getvalue())
            outfile.close()


class BuildableTemplateView(TemplateView, BuildableMixin):
    """
    Renders and builds a simple template.

    When inherited, the child class should include the following attributes.

        build_path:
            The target location of the built file in the BUILD_DIR.
            `index.html` would place it at the built site's root.
            `foo/index.html` would place it inside a subdirectory.

        template_name:
            The name of the template you would like Django to render.
    """
    @property
    def build_method(self):
        return self.build

    def build(self):
        logger.debug("Building %s" % self.template_name)
        build_path = self.get_build_path()
        self.request = self.create_request(build_path)
        path = os.path.join(settings.BUILD_DIR, build_path)
        self.prep_directory(build_path)
        self.build_file(path, self.get_content())

    def get_build_path(self):
        return six.text_type(self.build_path).lstrip('/')


class Buildable404View(BuildableTemplateView):
    """
    The default Django 404 page, but built out.
    """
    build_path = '404.html'
    template_name = '404.html'


class BuildableRedirectView(RedirectView, BuildableMixin):
    """
    Render and build a redirect.

    Required attributes:

        build_path:
            The URL being requested, which will be published as a flatfile
            with a redirect away from it.

        url:
            The URL where redirect will send the user. Operates
            in the same way as the standard generic RedirectView.
    """
    permanent = True

    def get_content(self):
        html = """
        <html>
            <head>
            <meta http-equiv="Refresh" content="1;url=%s" />
            </head>
            <body></body>
        </html>
        """
        html = html % self.get_redirect_url()
        return html.encode("utf-8")

    @property
    def build_method(self):
        return self.build

    def build(self):
        logger.debug("Building redirect from %s to %s" % (
            self.build_path,
            self.get_redirect_url()
        ))
        self.request = self.create_request(self.build_path)
        path = os.path.join(settings.BUILD_DIR, self.build_path)
        self.prep_directory(self.build_path)
        self.build_file(path, self.get_content())

    def get_redirect_url(self, *args, **kwargs):
        """
        Return the URL redirect to. Keyword arguments from the
        URL pattern match generating the redirect request
        are provided as kwargs to this method.
        """
        if self.url:
            url = self.url % kwargs
        elif self.pattern_name:
            try:
                url = reverse(self.pattern_name, args=args, kwargs=kwargs)
            except NoReverseMatch:
                return None
        else:
            return None
        return url

    def post_publish(self, bucket):
        logger.debug("Adding S3 redirect header from {} to in {} to {}".format(
            self.build_path,
            bucket.name,
            self.get_redirect_url()
        ))
        s3_client, s3_resource = get_s3_client()
        s3_client.copy_object(
            ACL='public-read',
            Bucket=bucket.name,
            CopySource={
                 'Bucket': bucket.name,
                 'Key': self.build_path
            },
            Key=self.build_path,
            WebsiteRedirectLocation=self.get_redirect_url()
        )
