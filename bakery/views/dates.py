"""
Views that inherit from Django's class-based generic views and add methods
for building flat files.
"""

import logging
import os
import shutil  # Added for rmtree
from datetime import date
from pathlib import Path  # Added for Path operations

from django.conf import settings
from django.views.generic.dates import (
    ArchiveIndexView,
    DayArchiveView,
    MonthArchiveView,
    YearArchiveView,
)

from bakery.views import BuildableMixin

# from fs import path # Removed fs import


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

    build_path = "archive/index.html"  # This is already a relative path string

    @property
    def build_method(self):
        return self.build_queryset

    def build_queryset(self):
        logger.debug("Building %s" % self.build_path)
        self.request = self.create_request(self.build_path)
        # self.build_path is a relative path string, suitable for prep_directory and build_file
        self.prep_directory(self.build_path)
        self.build_file(self.build_path, self.get_content())


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
        year = super().get_year()
        fmt = self.get_year_format()
        return date(int(year), 1, 1).strftime(fmt)

    def get_url(self):
        """
        The URL at which the detail page should appear.
        By default it is /archive/ + the year in self.year_format.
        """
        # os.path.join is fine for URL construction
        return os.path.join("/archive", self.get_year())

    def get_build_path(self):
        """
        Used to determine where to build the page. Returns a relative path string
        from BUILD_DIR. By default it will be self.get_url() + "/index.html".
        e.g., "archive/2023/index.html"
        """
        # self.get_url() returns a URL path like "/archive/2023"
        # We want a relative filesystem path like "archive/2023/index.html"
        return (Path(self.get_url().lstrip("/")) / "index.html").as_posix()

    def build_year(self, dt):
        """
        Build the page for the provided year.
        """
        self.year = str(dt.year)
        logger.debug("Building year: %s" % self.year)
        # get_url() is for the request context
        self.request = self.create_request(self.get_url())
        # get_build_path() now returns a relative path string
        relative_file_path = self.get_build_path()
        self.prep_directory(relative_file_path)
        self.build_file(relative_file_path, self.get_content())

    def build_dated_queryset(self):
        """
        Build pages for all years in the queryset.
        """
        qs = self.get_dated_queryset()
        if qs is None:  # Handle case where get_dated_queryset might return None
            logger.warning(
                "Dated queryset is None. Skipping build for %s.",
                self.__class__.__name__,
            )
            return
        date_list = self.get_date_list(qs)
        if date_list is None:
            logger.warning("Date list is None. Skipping build for %s.", self.__class__.__name__)
            return
        for dt_item in date_list:
            self.build_year(dt_item)

    def unbuild_year(self, dt):
        """
        Deletes the directory for the given year.
        e.g., if get_url() is /archive/2023, removes BUILD_DIR/archive/2023/
        """
        self.year = str(dt.year)
        logger.debug("Unbuilding year: %s" % self.year)
        # get_url() returns a URL path like "/archive/2023"
        # We want the corresponding directory relative to BUILD_DIR
        relative_dir_to_remove_str = self.get_url().lstrip("/")
        absolute_dir_to_remove = Path(settings.BUILD_DIR) / relative_dir_to_remove_str

        if absolute_dir_to_remove.exists() and absolute_dir_to_remove.is_dir():
            logger.debug(f"Removing directory {absolute_dir_to_remove}")
            shutil.rmtree(absolute_dir_to_remove)
        elif absolute_dir_to_remove.exists():
            logger.warning(
                f"Attempted to remove directory {absolute_dir_to_remove}, "
                f"but it is not a directory.",
            )
        else:
            logger.debug(f"Directory {absolute_dir_to_remove} does not exist. Nothing to unbuild.")


class BuildableMonthArchiveView(MonthArchiveView, BuildableMixin):
    """
    Renders and builds a monthly archive showing all objects in a given month.
    (Docstring continues...)
    """

    @property
    def build_method(self):
        return self.build_dated_queryset

    def get_year(self):
        """
        Return the year from the database in the format expected by the URL.
        """
        year = super().get_year()
        fmt = self.get_year_format()
        return date(int(year), 1, 1).strftime(fmt)

    def get_month(self):
        """
        Return the month from the database in the format expected by the URL.
        """
        year = super().get_year()
        month = super().get_month()
        fmt = self.get_month_format()
        return date(int(year), int(month), 1).strftime(fmt)

    def get_url(self):
        """
        The URL at which the detail page should appear.
        e.g., /archive/2016/01/.
        """
        return os.path.join("/archive", self.get_year(), self.get_month())

    def get_build_path(self):
        """
        Used to determine where to build the page. Returns a relative path string
        from BUILD_DIR. e.g., "archive/2023/01/index.html"
        """
        return (Path(self.get_url().lstrip("/")) / "index.html").as_posix()

    def build_month(self, dt):
        """
        Build the page for the provided month.
        """
        self.month = str(dt.month)
        self.year = str(dt.year)
        logger.debug("Building month: {}-{}".format(self.year, self.month))
        self.request = self.create_request(self.get_url())
        relative_file_path = self.get_build_path()
        self.prep_directory(relative_file_path)
        self.build_file(relative_file_path, self.get_content())

    def build_dated_queryset(self):
        """
        Build pages for all months in the queryset.
        """
        qs = self.get_dated_queryset()
        if qs is None:
            logger.warning(
                "Dated queryset is None. Skipping build for %s.",
                self.__class__.__name__,
            )
            return
        date_list = self.get_date_list(qs)
        if date_list is None:
            logger.warning("Date list is None. Skipping build for %s.", self.__class__.__name__)
            return
        for dt_item in date_list:
            self.build_month(dt_item)

    def unbuild_month(self, dt):
        """
        Deletes the directory for the given month.
        """
        self.year = str(dt.year)
        self.month = str(dt.month)
        logger.debug("Unbuilding month: {}-{}".format(self.year, self.month))
        relative_dir_to_remove_str = self.get_url().lstrip("/")
        absolute_dir_to_remove = Path(settings.BUILD_DIR) / relative_dir_to_remove_str

        if absolute_dir_to_remove.exists() and absolute_dir_to_remove.is_dir():
            logger.debug(f"Removing directory {absolute_dir_to_remove}")
            shutil.rmtree(absolute_dir_to_remove)
        elif absolute_dir_to_remove.exists():
            logger.warning(
                f"Attempted to remove directory {absolute_dir_to_remove}, "
                f"but it is not a directory.",
            )
        else:
            logger.debug(f"Directory {absolute_dir_to_remove} does not exist. Nothing to unbuild.")


class BuildableDayArchiveView(DayArchiveView, BuildableMixin):
    """
    Renders and builds a day archive showing all objects in a given day.
    (Docstring continues...)
    """

    @property
    def build_method(self):
        return self.build_dated_queryset

    def get_year(self):
        """
        Return the year from the database in the format expected by the URL.
        """
        year = super().get_year()
        fmt = self.get_year_format()
        dt_obj = date(int(year), 1, 1)
        return dt_obj.strftime(fmt)

    def get_month(self):
        """
        Return the month from the database in the format expected by the URL.
        """
        year = super().get_year()
        month = super().get_month()
        fmt = self.get_month_format()
        dt_obj = date(int(year), int(month), 1)
        return dt_obj.strftime(fmt)

    def get_day(self):
        """
        Return the day from the database in the format expected by the URL.
        """
        year = super().get_year()
        month = super().get_month()
        day = super().get_day()
        fmt = self.get_day_format()
        dt_obj = date(int(year), int(month), int(day))
        return dt_obj.strftime(fmt)

    def get_url(self):
        """
        The URL at which the detail page should appear.
        e.g., /archive/2016/01/01/.
        """
        return os.path.join(
            "/archive",
            self.get_year(),
            self.get_month(),
            self.get_day(),
        )

    def get_build_path(self):
        """
        Used to determine where to build the page. Returns a relative path string
        from BUILD_DIR. e.g., "archive/2023/01/01/index.html"
        """
        return (Path(self.get_url().lstrip("/")) / "index.html").as_posix()

    def build_day(self, dt):
        """
        Build the page for the provided day.
        """
        self.month = str(dt.month)
        self.year = str(dt.year)
        self.day = str(dt.day)
        logger.debug(
            "Building day: {}-{}-{}".format(self.year, self.month, self.day),
        )
        self.request = self.create_request(self.get_url())
        relative_file_path = self.get_build_path()
        self.prep_directory(relative_file_path)
        self.build_file(relative_file_path, self.get_content())

    def build_dated_queryset(self):
        """
        Build pages for all days in the queryset.
        """
        qs = self.get_dated_queryset()
        if qs is None:
            logger.warning(
                "Dated queryset is None. Skipping build for %s.",
                self.__class__.__name__,
            )
            return
        # Note: Django's get_date_list for DayArchiveView might need date_type="day"
        # but the default for DayArchiveView.get_date_list is already 'day'.
        date_list = self.get_date_list(qs)  # , date_type="day")
        if date_list is None:
            logger.warning("Date list is None. Skipping build for %s.", self.__class__.__name__)
            return
        for dt_item in date_list:
            self.build_day(dt_item)

    def unbuild_day(self, dt):
        """
        Deletes the directory for the given day.
        """
        self.year = str(dt.year)
        self.month = str(dt.month)
        self.day = str(dt.day)
        logger.debug(
            "Unbuilding day: {}-{}-{}".format(self.year, self.month, self.day),
        )
        relative_dir_to_remove_str = self.get_url().lstrip("/")
        absolute_dir_to_remove = Path(settings.BUILD_DIR) / relative_dir_to_remove_str

        if absolute_dir_to_remove.exists() and absolute_dir_to_remove.is_dir():
            logger.debug(f"Removing directory {absolute_dir_to_remove}")
            shutil.rmtree(absolute_dir_to_remove)
        elif absolute_dir_to_remove.exists():
            logger.warning(
                f"Attempted to remove directory {absolute_dir_to_remove}, "
                f"but it is not a directory.",
            )
        else:
            logger.debug(f"Directory {absolute_dir_to_remove} does not exist. Nothing to unbuild.")
