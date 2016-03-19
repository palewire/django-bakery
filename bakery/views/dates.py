import os
import shutil
import logging
from datetime import date
from django.conf import settings
from bakery.views import BuildableMixin
from django.test.client import RequestFactory
from django.views.generic.dates import (
    ArchiveIndexView,
    YearArchiveView,
    MonthArchiveView,
)
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


class BuildableYearArchiveView(YearArchiveView, BuildableMixin):
    """
    Renders and builds a yearly archive showing all available months
    (and, if you'd like, objects) in a given year.

    Required attributes:

        model or queryset:
            Where the list of objects should come from. Must be a queryset
            object, not a list.

        template_name:
            The name of the template you would like Django to render. You need
            to override this if you don't want to rely on the Django defaults.
    """
    @property
    def build_method(self):
        return self.build_dated_queryset

    def get_year(self):
        """
        Return the year from the database in the format expected by the URL.
        """
        fmt = self.get_year_format()
        return date(int(self.year), 1, 1).strftime(fmt)

    def get_url(self):
        """
        The URL at which the detail page should appear.

        By default it is /archive/ + the year in self.year_format.
        """
        return os.path.join('/archive',self.get_year())

    def get_build_path(self):
        """
        Used to determine where to build the page. Override this if you
        would like your page at a different location. By default it
        will be built at self.get_url() + "/index.html"
        """
        path = os.path.join(settings.BUILD_DIR, self.get_url()[1:])
        os.path.exists(path) or os.makedirs(path)
        return os.path.join(path, 'index.html')

    def build_year(self, dt):
        """
        Build the page for the provided year.
        """
        self.year = str(dt.year)
        logger.debug("Building %s" % self.year)
        self.request = RequestFactory().get(self.get_url())
        path = self.get_build_path()
        self.build_file(path, self.get_content())

    def build_dated_queryset(self):
        """
        Build pages for all years in the queryset.
        """
        qs = self.get_dated_queryset()
        years = self.get_date_list(qs)
        [self.build_year(dt) for dt in years]

    def unbuild_year(self, dt):
        """
        Deletes the directory at self.get_build_path.
        """
        self.year = str(dt.year)
        logger.debug("Unbuilding %s" % self.year)
        path = os.path.split(self.get_build_path())[0]
        if os.path.exists(path):
            shutil.rmtree(path)


class BuildableMonthArchiveView(MonthArchiveView, BuildableMixin):
    pass
