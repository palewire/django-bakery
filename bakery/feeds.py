import os
import six
import logging
from django.conf import settings
from bakery.views import BuildableMixin
from django.contrib.syndication.views import Feed
logger = logging.getLogger(__name__)


class BuildableFeed(Feed, BuildableMixin):
    """
    Extends the base Django Feed class to be buildable.
    """
    build_path = 'feed.xml'

    def get_content(self, *args, **kwargs):
        return self(self.request, *args, **kwargs).content

    @property
    def build_method(self):
        return self.build_queryset

    def _get_bakery_dynamic_attr(self, attname, obj, args=None, default=None):
        """
        Allows subclasses to provide an attribute (say, 'foo') in three
        different ways: As a fixed class-level property or as a method
        foo(self) or foo(self, obj). The second argument argument 'obj' is
        the "subject" of the current Feed invocation. See the Django Feed
        documentation for details.

        This method was shamelessly stolen from the Feed class and extended
        with the ability to pass additional arguments to subclass methods.
        """
        try:
            attr = getattr(self, attname)
        except AttributeError:
            return default

        if callable(attr) or args:
            args = args[:] if args else []

            # Check co_argcount rather than try/excepting the function and
            # catching the TypeError, because something inside the function
            # may raise the TypeError. This technique is more accurate.
            try:
                code = six.get_function_code(attr)
            except AttributeError:
                code = six.get_function_code(attr.__call__)
            if code.co_argcount == 2 + len(args):  # one argument is 'self'
                args.append(obj)
            return attr(*args)

        return attr

    def get_queryset(self):
        return [None]

    def build_queryset(self):
        for obj in self.get_queryset():
            build_path = self._get_bakery_dynamic_attr('build_path', obj)
            url = self._get_bakery_dynamic_attr('feed_url', obj)

            logger.debug("Building %s" % build_path)

            self.request = self._get_bakery_dynamic_attr(
                'create_request',
                obj,
                args=[url or build_path]
            )

            self.prep_directory(build_path)
            path = os.path.join(settings.BUILD_DIR, build_path)
            content = self._get_bakery_dynamic_attr('get_content', obj)
            self.build_file(path, content)
