"""
Views that inherit from Django's class-based generic views and add methods
for building flat files.
"""
import os
import six
import sys
import gzip
import shutil
import logging
import mimetypes
from django.conf import settings
from bakery import DEFAULT_GZIP_CONTENT_TYPES
from django.test.client import RequestFactory
from django.views.generic import ListView, RedirectView
from django.views.generic import TemplateView, DetailView
from django.core.urlresolvers import reverse, NoReverseMatch
logger = logging.getLogger(__name__)


class BuildableMixin(object):
    """
    Common methods we will use in buildable views.
    """
    def get_content(self):
        """
        How to render the HTML or other content for the page.

        If you choose to render using something other than a Django template,
        like HttpResponse for instance, you will want to override this.
        """
        return self.get(self.request).render().content

    def prep_directory(self, path):
        """
        Prepares a new directory to store the file at the provided path,
        if needed.
        """
        dirname = os.path.dirname(path)
        if dirname:
            dirname = os.path.join(settings.BUILD_DIR, dirname)
            os.path.exists(dirname) or os.makedirs(dirname)

    def build_file(self, path, html):
        if self.is_gzippable(path):
            self.gzip_file(path, html)
        else:
            self.write_file(path, html)

    def write_file(self, path, html):
        """
        Writes out the provided HTML to the provided path.
        """
        logger.debug("Building HTML file to %s" % path)
        outfile = open(path, 'wb')
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

    def gzip_file(self, path, html):
        """
        Zips up the provided HTML as a companion for the provided path.

        Intended to take advantage of the peculiarities of
        Amazon S3's GZIP service.

        mtime, an option that writes a timestamp to the output file
        is set to 0, to avoid having s3cmd do unnecessary uploads because
        of differences in the timestamp
        """
        logger.debug("Building gzipped HTML file to %s" % path)
        if float(sys.version[:3]) >= 2.7:
            outfile = gzip.GzipFile(path, 'wb', mtime=0)
        else:
            outfile = gzip.GzipFile(path, 'wb')
        outfile.write(six.binary_type(html))
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
        self.request = RequestFactory().get(self.build_path)
        path = os.path.join(settings.BUILD_DIR, self.build_path)
        self.prep_directory(self.build_path)
        self.build_file(path, self.get_content())


class BuildableListView(ListView, BuildableMixin):
    """
    Render and builds a page about a list of objects.

    Required attributes:

        model or queryset:
            Where the list of objects should come from. `self.queryset` can
            be any iterable of items, not just a queryset.

        build_path:
            The target location of the built file in the BUILD_DIR.
            `index.html` would place it at the built site's root.
            `foo/index.html` would place it inside a subdirectory.
            `index.html is the default.

        template_name:
            The name of the template you would like Django to render. You need
            to override this if you don't want to rely on the Django defaults.
    """
    build_path = 'index.html'

    @property
    def build_method(self):
        return self.build_queryset

    def build_queryset(self):
        logger.debug("Building %s" % self.build_path)
        self.request = RequestFactory().get(self.build_path)
        self.prep_directory(self.build_path)
        path = os.path.join(settings.BUILD_DIR, self.build_path)
        self.build_file(path, self.get_content())


class BuildableDetailView(DetailView, BuildableMixin):
    """
    Render and build a "detail" view of an object.

    Required attributes:

        queryset:
            the model instance the objects are looked up from.

        template_name:
            The name of the template you would like Django to render. You need
            to override this if you don't want to rely on the Django defaults.
    """
    @property
    def build_method(self):
        return self.build_queryset

    def get_url(self, obj):
        """
        The URL at which the detail page should appear.
        """
        return obj.get_absolute_url()

    def get_build_path(self, obj):
        """
        Used to determine where to build the detail page. Override this if you
        would like your detail page at a different location. By default it
        will be built at get_url() + "index.html"
        """
        path = os.path.join(settings.BUILD_DIR, self.get_url(obj)[1:])
        os.path.exists(path) or os.makedirs(path)
        return os.path.join(path, 'index.html')

    def set_kwargs(self, obj):
        slug_field = self.get_slug_field()
        self.kwargs = {
            'pk': getattr(obj, 'pk', None),
            slug_field: getattr(obj, slug_field, None),
            # Also alias the slug_field to the key `slug`
            # so it can work for people who just toss that in
            'slug': getattr(obj, slug_field, None),
        }

    def build_object(self, obj):
        logger.debug("Building %s" % obj)
        self.request = RequestFactory().get(self.get_url(obj))
        self.set_kwargs(obj)
        path = self.get_build_path(obj)
        self.build_file(path, self.get_content())

    def build_queryset(self):
        [self.build_object(o) for o in self.get_queryset().all()]

    def unbuild_object(self, obj):
        """
        Deletes the directory at self.get_build_path.
        """
        logger.debug("Unbuilding %s" % obj)
        path = os.path.split(self.get_build_path(obj))[0]
        if os.path.exists(path):
            shutil.rmtree(path)


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
        self.request = RequestFactory().get(self.build_path)
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
        logger.debug("Adding S3 redirect header from %s to %s" % (
            self.build_path,
            self.get_redirect_url()
        ))
        key = bucket.get_key(self.build_path)
        key.copy(
            key.bucket,
            key.name,
            preserve_acl=True,
            metadata={'Content-Type': 'text/html'}
        )
        key.set_redirect(self.get_redirect_url())
        key.make_public()
