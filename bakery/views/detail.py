"""
Views that inherit from Django's class-based generic views and add methods
for building flat files.
"""

import logging
import os
from collections.abc import Callable
from os import PathLike
from typing import Protocol, cast, runtime_checkable

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.views.generic import DetailView
from fs import path

from .base import BuildableMixin

logger = logging.getLogger(__name__)


@runtime_checkable
class _HasAbsoluteUrl(Protocol):
    def get_absolute_url(self) -> str: ...


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
    def build_method(self) -> Callable[[], None]:
        return self.build_queryset

    def get_url(self, obj: object) -> str:
        """
        The URL at which the detail page should appear.
        """
        if not isinstance(obj, _HasAbsoluteUrl) or not obj.get_absolute_url():
            raise ImproperlyConfigured(
                f"No URL configured. You must either \
set a ``get_absolute_url`` method on the {obj.__class__.__name__} model or override the {self.__class__.__name__} view's \
``get_url`` method"
            )
        return obj.get_absolute_url()

    def get_build_path(self, obj: object) -> str:
        """
        Used to determine where to build the detail page. Override this if you
        would like your detail page at a different location. By default it
        will be built at get_url() + "index.html"
        """
        target_path = path.join(
            str(cast("str | PathLike[str]", settings.BUILD_DIR)),
            self.get_url(obj).lstrip("/"),
        )
        if not self.fs.exists(target_path):
            logger.debug("Creating %s", target_path)
            self.fs.makedirs(target_path)
        return cast("str", path.join(target_path, "index.html"))

    def set_kwargs(self, obj: object) -> None:
        slug_field = self.get_slug_field()
        self.kwargs = {
            "pk": getattr(obj, "pk", None),
            slug_field: getattr(obj, slug_field, None),
            # Also alias the slug_field to the key `slug`
            # so it can work for people who just toss that in
            "slug": getattr(obj, slug_field, None),
        }

    def build_object(self, obj: object) -> None:
        logger.debug("Building %s", obj)
        self.request = self.create_request(self.get_url(obj))
        self.set_kwargs(obj)
        target_path = self.get_build_path(obj)
        self.build_file(target_path, self.get_content())

    def build_queryset(self) -> None:
        [self.build_object(o) for o in self.get_queryset().all()]

    def unbuild_object(self, obj: object) -> None:
        """
        Deletes the directory at self.get_build_path.
        """
        logger.debug("Unbuilding %s", obj)
        target_path = os.path.split(self.get_build_path(obj))[0]
        if self.fs.exists(target_path):
            logger.debug("Removing %s", target_path)
            self.fs.removetree(target_path)
