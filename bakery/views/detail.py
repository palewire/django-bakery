"""
Views that inherit from Django's class-based generic views and add methods
for building flat files.
"""

import logging
import os
from pathlib import Path

from django.views.generic import DetailView

from .base import BuildableMixin

logger = logging.getLogger(__name__)


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
        if not hasattr(obj, "get_absolute_url") or not obj.get_absolute_url():  # noqa: E501
            raise ImproperlyConfigured(  # noqa: F821
                f"No URL configured. You must either set a "
                f"``get_absolute_url`` method on the {obj.__class__.__name__} "
                f"model or override the {self.__class__.__name__} view's "
                f"``get_url`` method",  # noqa: E501
            )  # noqa: E501
        return obj.get_absolute_url()

    def get_build_path(self, obj):
        """
        Used to determine where to build the detail page. Override this if you
        would like your detail page at a different location. By default it
        will be built at get_url() + "index.html"
        """
        target_path = Path(self.build_dir) / self.get_url(obj).lstrip("/")
        if not target_path.exists():
            logger.debug(f"Creating {target_path}")
            target_path.mkdir(parents=True, exist_ok=True)
        return target_path / "index.html"

    def build_file(self, path, content):
        """
        Writes the file to disk.
        """
        path.write_text(content)

    def set_kwargs(self, obj):
        """
        Sets the kwargs necessary to render the detail view.
        """
        slug_field = self.get_slug_field()
        self.kwargs = {
            "pk": getattr(obj, "pk", None),
            slug_field: getattr(obj, slug_field, None),
            # Also alias the slug_field to the key `slug`
            # so it can work for people who just toss that in
            "slug": getattr(obj, slug_field, None),
        }

    def build_object(self, obj):
        """
        Builds the detail page for a single object.
        """
        logger.debug("Building %s" % obj)
        self.request = self.create_request(self.get_url(obj))
        self.set_kwargs(obj)
        target_path = self.get_build_path(obj)
        self.build_file(target_path, self.get_content())

    def build_queryset(self):
        """
        Builds the detail page for each object in the queryset.
        """
        [self.build_object(o) for o in self.get_queryset().all()]

    def unbuild_object(self, obj):
        """
        Deletes the directory at self.get_build_path.
        """
        logger.debug(f"Unbuilding {obj}")
        target_path = self.get_build_path(obj).parent
        if target_path.exists():
            logger.debug(f"Removing {target_path}")
            os.rmdir(target_path)
