import os
import logging
from django.conf import settings
from bakery.views import BuildableMixin
from django.test.client import RequestFactory
from django.views.generic import ArchiveIndexView
logger = logging.getLogger(__name__)


class BuildableArchiveIndexView(ArchiveIndexView, BuildableMixin):
    """
    Renders and builds a top-level archive of date-based items.

    Required attributes:

        model or queryset:
            Where the list of objects should come from. `self.queryset` can
            be any iterable of items, not just a queryset.

        build_path:
            The target location of the built file in the BUILD_DIR.
            `index.html` would place it at the built site's root.
            `archive/index.html` would place it inside a subdirectory.
            `archive/index.html is the default.

        template_name:
            The name of the template you would like Django to render. You need
            to override this if you don't want to rely on the Django defaults.

    """
    build_path = 'archive/index.html'

    @property
    def build_method(self):
        return self.build_queryset

    def build_queryset(self):
        logger.debug("Building %s" % self.build_path)
        self.request = RequestFactory().get(self.build_path)
        self.prep_directory(self.build_path)
        path = os.path.join(settings.BUILD_DIR, self.build_path)
        self.build_file(path, self.get_content())
