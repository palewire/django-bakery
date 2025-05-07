# C:/dev/git_clones/django-bakery/bakery/views/dates.py
import logging
import os
import shutil
from datetime import date
from pathlib import Path

from django.conf import settings
from django.views.generic.dates import (
    ArchiveIndexView,
    DayArchiveView,
    MonthArchiveView,
    YearArchiveView,
)

# Assuming BuildableMixin is in bakery.views.base
from bakery.views.base import BuildableMixin

logger = logging.getLogger(__name__)


class BuildableArchiveIndexView(ArchiveIndexView, BuildableMixin):
    build_path = "archive/index.html"

    @property
    def build_method(self):
        return self.build_queryset

    def build_queryset(self):
        logger.debug("Building %s" % self.build_path)
        self.request = self.create_request(self.build_path)
        # self.prep_directory(self.build_path) # REMOVE THIS LINE
        self.build_file(self.build_path, self.get_content())


class BuildableYearArchiveView(YearArchiveView, BuildableMixin):
    @property
    def build_method(self):
        return self.build_dated_queryset

    def get_year(self):
        year = super().get_year()
        fmt = self.get_year_format()
        return date(int(year), 1, 1).strftime(fmt)

    def get_url(self):
        return os.path.join("/archive", self.get_year())

    def get_build_path(self):
        return (Path(self.get_url().lstrip("/")) / "index.html").as_posix()

    def build_year(self, dt):
        self.year = str(dt.year)
        logger.debug("Building year: %s" % self.year)
        self.request = self.create_request(self.get_url())
        relative_file_path = self.get_build_path()
        logger.info(
            f"[{self.get_class_name()}] Relative file path for {dt.year}: {relative_file_path}",
        )
        try:
            content = self.get_content()
            logger.info(
                f"[{self.get_class_name()}] Got content for {dt.year}, length: {len(content)}",
            )
            # self.prep_directory(relative_file_path) # REMOVE THIS LINE
            self.build_file(
                relative_file_path,
                content,
            )  # Changed from self.get_content() to content
        except Exception as e:
            logger.error(
                f"[{self.get_class_name()}] Error getting content or "
                f"building file for {dt.year}: {type(e)}, {e}, {e.args}",
            )

    def build_dated_queryset(self):
        qs = self.get_dated_queryset()
        if qs is None:
            logger.warning(
                "Dated queryset is None. Skipping build for %s.",
                self.get_class_name(),
            )
            return
        date_list = self.get_date_list(qs)
        if date_list is None:
            logger.warning("Date list is None. Skipping build for %s.", self.get_class_name())
            return
        for dt_item in date_list:
            logger.info(f"[{self.get_class_name()}] Processing year: {dt_item}")
            self.build_year(dt_item)

    def unbuild_year(self, dt):
        self.year = str(dt.year)
        logger.debug("Unbuilding year: %s" % self.year)
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
    @property
    def build_method(self):
        return self.build_dated_queryset

    def get_year(self):
        year = super().get_year()
        fmt = self.get_year_format()
        return date(int(year), 1, 1).strftime(fmt)

    def get_month(self):
        year = super().get_year()
        month = super().get_month()
        fmt = self.get_month_format()
        return date(int(year), int(month), 1).strftime(fmt)

    def get_url(self):
        return os.path.join("/archive", self.get_year(), self.get_month())

    def get_build_path(self):
        return (Path(self.get_url().lstrip("/")) / "index.html").as_posix()

    def build_month(self, dt):
        self.month = str(dt.month)
        self.year = str(dt.year)
        logger.debug("Building month: {}-{}".format(self.year, self.month))
        self.request = self.create_request(self.get_url())
        relative_file_path = self.get_build_path()
        # self.prep_directory(relative_file_path) # REMOVE THIS LINE
        self.build_file(relative_file_path, self.get_content())

    def build_dated_queryset(self):
        qs = self.get_dated_queryset()
        if qs is None:
            logger.warning(
                "Dated queryset is None. Skipping build for %s.",
                self.get_class_name(),
            )
            return
        date_list = self.get_date_list(qs)
        if date_list is None:
            logger.warning("Date list is None. Skipping build for %s.", self.get_class_name())
            return
        for dt_item in date_list:
            self.build_month(dt_item)

    def unbuild_month(self, dt):
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
    @property
    def build_method(self):
        return self.build_dated_queryset

    def get_year(self):
        year = super().get_year()
        fmt = self.get_year_format()
        dt_obj = date(int(year), 1, 1)
        return dt_obj.strftime(fmt)

    def get_month(self):
        year = super().get_year()
        month = super().get_month()
        fmt = self.get_month_format()
        dt_obj = date(int(year), int(month), 1)
        return dt_obj.strftime(fmt)

    def get_day(self):
        year = super().get_year()
        month = super().get_month()
        day = super().get_day()
        fmt = self.get_day_format()
        dt_obj = date(int(year), int(month), int(day))
        return dt_obj.strftime(fmt)

    def get_url(self):
        return os.path.join(
            "/archive",
            self.get_year(),
            self.get_month(),
            self.get_day(),
        )

    def get_build_path(self):
        return (Path(self.get_url().lstrip("/")) / "index.html").as_posix()

    def build_day(self, dt):
        self.month = str(dt.month)
        self.year = str(dt.year)
        self.day = str(dt.day)
        logger.debug(
            "Building day: {}-{}-{}".format(self.year, self.month, self.day),
        )
        self.request = self.create_request(self.get_url())
        relative_file_path = self.get_build_path()
        # self.prep_directory(relative_file_path) # REMOVE THIS LINE
        self.build_file(relative_file_path, self.get_content())

    def build_dated_queryset(self):
        qs = self.get_dated_queryset()
        if qs is None:
            logger.warning(
                "Dated queryset is None. Skipping build for %s.",
                self.get_class_name(),
            )
            return
        date_list = self.get_date_list(qs)
        if date_list is None:
            logger.warning("Date list is None. Skipping build for %s.", self.get_class_name())
            return
        for dt_item in date_list:
            self.build_day(dt_item)

    def unbuild_day(self, dt):
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
