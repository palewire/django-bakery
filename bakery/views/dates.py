"""
Views that inherit from Django's class-based generic views and add methods
for building flat files.
"""
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
    DayArchiveView,
)
logger = logging.getLogger(__name__)


class BuildableArchiveIndexView(ArchiveIndexView, BuildableMixin):
    """
    Renders and builds a top-level index page showing the "latest" objects,
    by date.

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
        return os.path.join('/archive', self.get_year())

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
    """
    Renders and builds a monthly archive showing all objects in a given month.

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

    def get_month(self):
        """
        Return the month from the database in the format expected by the URL.
        """
        fmt = self.get_month_format()
        return date(int(self.year), int(self.month), 1).strftime(fmt)

    def get_url(self):
        """
        The URL at which the detail page should appear.

        By default it is /archive/ + the year in self.year_format + the
        month in self.month_format. An example would be /archive/2016/01/.
        """
        return os.path.join('/archive', self.get_year(), self.get_month())

    def get_build_path(self):
        """
        Used to determine where to build the page. Override this if you
        would like your page at a different location. By default it
        will be built at self.get_url() + "/index.html"
        """
        path = os.path.join(settings.BUILD_DIR, self.get_url()[1:])
        os.path.exists(path) or os.makedirs(path)
        return os.path.join(path, 'index.html')

    def build_month(self, dt):
        """
        Build the page for the provided month.
        """
        self.month = str(dt.month)
        self.year = str(dt.year)
        logger.debug("Building %s-%s" % (self.year, self.month))
        self.request = RequestFactory().get(self.get_url())
        path = self.get_build_path()
        self.build_file(path, self.get_content())

    def build_dated_queryset(self):
        """
        Build pages for all years in the queryset.
        """
        qs = self.get_dated_queryset()
        months = self.get_date_list(qs)
        [self.build_month(dt) for dt in months]

    def unbuild_month(self, dt):
        """
        Deletes the directory at self.get_build_path.
        """
        self.year = str(dt.year)
        self.month = str(dt.month)
        logger.debug("Building %s-%s" % (self.year, self.month))
        path = os.path.split(self.get_build_path())[0]
        if os.path.exists(path):
            shutil.rmtree(path)


class BuildableDayArchiveView(DayArchiveView, BuildableMixin):
    """
    Renders and builds a day archive showing all objects in a given day.

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
        dt = date(int(self.year), int(self.month), int(self.day))
        return dt.strftime(fmt)

    def get_month(self):
        """
        Return the month from the database in the format expected by the URL.
        """
        fmt = self.get_month_format()
        dt = date(int(self.year), int(self.month), int(self.day))
        return dt.strftime(fmt)

    def get_day(self):
        """
        Return the day from the database in the format expected by the URL.
        """
        fmt = self.get_day_format()
        dt = date(int(self.year), int(self.month), int(self.day))
        return dt.strftime(fmt)

    def get_url(self):
        """
        The URL at which the detail page should appear.

        By default it is /archive/ + the year in self.year_format + the
        month in self.month_format + the day in the self.day_format.
        An example would be /archive/2016/01/01/.
        """
        return os.path.join(
            '/archive',
            self.get_year(),
            self.get_month(),
            self.get_day()
        )

    def get_build_path(self):
        """
        Used to determine where to build the page. Override this if you
        would like your page at a different location. By default it
        will be built at self.get_url() + "/index.html"
        """
        path = os.path.join(settings.BUILD_DIR, self.get_url()[1:])
        os.path.exists(path) or os.makedirs(path)
        return os.path.join(path, 'index.html')

    def build_day(self, dt):
        """
        Build the page for the provided day.
        """
        self.month = str(dt.month)
        self.year = str(dt.year)
        self.day = str(dt.day)
        logger.debug("Building %s-%s-%s" % (self.year, self.month, self.day))
        self.request = RequestFactory().get(self.get_url())
        path = self.get_build_path()
        self.build_file(path, self.get_content())

    def build_dated_queryset(self):
        """
        Build pages for all years in the queryset.
        """
        qs = self.get_dated_queryset()
        days = self.get_date_list(qs, date_type='day')
        [self.build_day(dt) for dt in days]

    def unbuild_day(self, dt):
        """
        Deletes the directory at self.get_build_path.
        """
        self.year = str(dt.year)
        self.month = str(dt.month)
        self.day = str(dt.day)
        logger.debug("Building %s-%s-%s" % (self.year, self.month, self.day))
        path = os.path.split(self.get_build_path())[0]
        if os.path.exists(path):
            shutil.rmtree(path)
