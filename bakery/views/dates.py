"""
Views that inherit from Django's class-based generic views and add methods
for building flat files.
"""

import logging
import posixpath
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import cast

from django.views.generic.dates import (
    ArchiveIndexView,
    DayArchiveView,
    MonthArchiveView,
    YearArchiveView,
)

from bakery.filesystem import join_path
from bakery.views import BuildableMixin

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

    build_path = "archive/index.html"

    @property
    def build_method(self) -> Callable[[], None]:
        return self.build_queryset

    def build_queryset(self) -> None:
        logger.debug("Building %s", self.build_path)
        self.request = self.create_request(self.build_path)
        target_path = self.get_output_path(self.build_path)
        self.prep_directory(self.build_path)
        self.build_file(target_path, self.get_content())


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
    def build_method(self) -> Callable[[], None]:
        return self.build_dated_queryset

    def get_year(self) -> str:
        """
        Return the year from the database in the format expected by the URL.
        """
        year = cast("str", super().get_year())
        fmt = self.get_year_format()
        return date(int(year), 1, 1).strftime(fmt)

    def get_url(self) -> str:
        """
        The URL at which the detail page should appear.

        By default it is /archive/ + the year in self.year_format.
        """
        return str(Path("/archive") / self.get_year())

    def get_build_path(self) -> str:
        """
        Used to determine where to build the page. Override this if you
        would like your page at a different location. By default it
        will be built at self.get_url() + "/index.html"
        """
        target_path = self.get_output_path(
            join_path(self.get_url().lstrip("/"), "index.html")
        )
        self._prep_output_directory(target_path)
        return target_path

    def build_year(self, dt: date) -> None:
        """
        Build the page for the provided year.
        """
        self.year = str(dt.year)
        logger.debug("Building %s", self.year)
        self.request = self.create_request(self.get_url())
        target_path = self.get_build_path()
        self.build_file(target_path, self.get_content())

    def build_dated_queryset(self) -> None:
        """
        Build pages for all years in the queryset.
        """
        qs = self.get_dated_queryset()
        years = self.get_date_list(qs)
        for dt in years:
            self.build_year(dt)

    def unbuild_year(self, dt: date) -> None:
        """
        Deletes the directory at self.get_build_path.
        """
        self.year = str(dt.year)
        logger.debug("Unbuilding %s", self.year)
        target_path = posixpath.dirname(self.get_build_path())
        if self.fs.exists(target_path):
            logger.debug("Removing %s", target_path)
            self.fs.removetree(target_path)


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
    def build_method(self) -> Callable[[], None]:
        return self.build_dated_queryset

    def get_year(self) -> str:
        """
        Return the year from the database in the format expected by the URL.
        """
        year = cast("str", super().get_year())
        fmt = self.get_year_format()
        return date(int(year), 1, 1).strftime(fmt)

    def get_month(self) -> str:
        """
        Return the month from the database in the format expected by the URL.
        """
        year = cast("str", super().get_year())
        month = cast("str", super().get_month())
        fmt = self.get_month_format()
        return date(int(year), int(month), 1).strftime(fmt)

    def get_url(self) -> str:
        """
        The URL at which the detail page should appear.

        By default it is /archive/ + the year in self.year_format + the
        month in self.month_format. An example would be /archive/2016/01/.
        """
        return str(Path("/archive") / self.get_year() / self.get_month())

    def get_build_path(self) -> str:
        """
        Used to determine where to build the page. Override this if you
        would like your page at a different location. By default it
        will be built at self.get_url() + "/index.html"
        """
        target_path = self.get_output_path(
            join_path(self.get_url().lstrip("/"), "index.html")
        )
        self._prep_output_directory(target_path)
        return target_path

    def build_month(self, dt: date) -> None:
        """
        Build the page for the provided month.
        """
        self.month = str(dt.month)
        self.year = str(dt.year)
        logger.debug("Building %s-%s", self.year, self.month)
        self.request = self.create_request(self.get_url())
        path = self.get_build_path()
        self.build_file(path, self.get_content())

    def build_dated_queryset(self) -> None:
        """
        Build pages for all years in the queryset.
        """
        qs = self.get_dated_queryset()
        months = self.get_date_list(qs)
        for dt in months:
            self.build_month(dt)

    def unbuild_month(self, dt: date) -> None:
        """
        Deletes the directory at self.get_build_path.
        """
        self.year = str(dt.year)
        self.month = str(dt.month)
        logger.debug("Building %s-%s", self.year, self.month)
        target_path = posixpath.dirname(self.get_build_path())
        if self.fs.exists(target_path):
            logger.debug("Removing %s", target_path)
            self.fs.removetree(target_path)


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
    def build_method(self) -> Callable[[], None]:
        return self.build_dated_queryset

    def get_year(self) -> str:
        """
        Return the year from the database in the format expected by the URL.
        """
        year = cast("str", super().get_year())
        fmt = self.get_year_format()
        dt = date(int(year), 1, 1)
        return dt.strftime(fmt)

    def get_month(self) -> str:
        """
        Return the month from the database in the format expected by the URL.
        """
        year = cast("str", super().get_year())
        month = cast("str", super().get_month())
        fmt = self.get_month_format()
        dt = date(int(year), int(month), 1)
        return dt.strftime(fmt)

    def get_day(self) -> str:
        """
        Return the day from the database in the format expected by the URL.
        """
        year = cast("str", super().get_year())
        month = cast("str", super().get_month())
        day = cast("str", super().get_day())
        fmt = self.get_day_format()
        dt = date(int(year), int(month), int(day))
        return dt.strftime(fmt)

    def get_url(self) -> str:
        """
        The URL at which the detail page should appear.

        By default it is /archive/ + the year in self.year_format + the
        month in self.month_format + the day in the self.day_format.
        An example would be /archive/2016/01/01/.
        """
        return str(
            Path("/archive") / self.get_year() / self.get_month() / self.get_day()
        )

    def get_build_path(self) -> str:
        """
        Used to determine where to build the page. Override this if you
        would like your page at a different location. By default it
        will be built at self.get_url() + "/index.html"
        """
        target_path = self.get_output_path(
            join_path(self.get_url().lstrip("/"), "index.html")
        )
        self._prep_output_directory(target_path)
        return target_path

    def build_day(self, dt: date) -> None:
        """
        Build the page for the provided day.
        """
        self.month = str(dt.month)
        self.year = str(dt.year)
        self.day = str(dt.day)
        logger.debug("Building %s-%s-%s", self.year, self.month, self.day)
        self.request = self.create_request(self.get_url())
        path = self.get_build_path()
        self.build_file(path, self.get_content())

    def build_dated_queryset(self) -> None:
        """
        Build pages for all years in the queryset.
        """
        qs = self.get_dated_queryset()
        days = self.get_date_list(qs, date_type="day")
        for dt in days:
            self.build_day(dt)

    def unbuild_day(self, dt: date) -> None:
        """
        Deletes the directory at self.get_build_path.
        """
        self.year = str(dt.year)
        self.month = str(dt.month)
        self.day = str(dt.day)
        logger.debug("Building %s-%s-%s", self.year, self.month, self.day)
        target_path = posixpath.dirname(self.get_build_path())
        if self.fs.exists(target_path):
            logger.debug("Removing %s", target_path)
            self.fs.removetree(target_path)
