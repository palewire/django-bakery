# C:/dev/git_clones/django-bakery/bakery/views/detail.py
import logging
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.views.generic.detail import DetailView

# Ensure this import path is correct and bakery.views.base.py is up-to-date
from bakery.views.base import BuildableMixin

logger = logging.getLogger(__name__)


class BuildableDetailView(DetailView, BuildableMixin):
    """
    Renders and builds a "detail" view of an object.

    Required attributes:
        model or queryset:
            Where the list of objects should come from. `self.queryset` can
            be any iterable of items, not just a queryset.
        template_name:
            The name of the template you would like Django to render. You need
            to override this if you don't want to rely on the Django defaults.
    """

    def get_url(self, obj=None):
        """
        The URL at which the detail page should appear.
        Pass in an object to get the URL for that object.
        """
        if obj is None:  # pragma: no cover
            # This path is taken if get_url is called without an object.
            # It relies on get_object() to resolve the current object.
            obj = self.get_object()
        try:
            return obj.get_absolute_url()
        except AttributeError:
            # This will be raised if the object 'obj' does not have a
            # get_absolute_url method, or if that method itself raises
            # an AttributeError (e.g., if it calls super() on a base
            # that doesn't have it).
            raise ImproperlyConfigured(
                f"Either {obj.__class__} must define .get_absolute_url() "
                "or the View class must override .get_url().",
            ) from AttributeError

    def get_object(self, queryset=None):
        """
        Return the object the view is displaying.
        For the build process, if self.object is already set (e.g., by
        BuildableMixin.get_content when called from self.build_object),
        use that directly. This bypasses the need for URL kwargs during builds.
        """
        if hasattr(self, "object") and self.object is not None:
            # If a queryset is provided, Django's DetailView.get_object
            # would normally check if self.object is an instance of queryset.model.
            # We can replicate that or trust that the build process sets the correct object.
            if queryset is not None and not isinstance(
                self.object,
                queryset.model,
            ):  # pragma: no cover
                logger.warning(
                    f"Pre-set self.object (type: {type(self.object)}) is not an instance of "
                    f"queryset.model ({queryset.model}). Falling back to super().get_object().",
                )
                # Falling back might re-introduce issues if self.kwargs is not set,
                # so this path should be avoided in build contexts.
                if not hasattr(self, "kwargs"):
                    self.kwargs = {}  # Ensure kwargs exists for super call
                return super().get_object(queryset)
            return self.object

        # If not in a build context where self.object is pre-set,
        # or if self.object was None, proceed with standard Django logic.
        # Ensure self.kwargs exists before calling super().get_object(),
        # as it relies on URL parameters passed via kwargs.
        if not hasattr(self, "kwargs"):
            self.kwargs = {}  # Provide default empty kwargs for safety

        return super().get_object(queryset)

    def get_build_path(self, obj) -> str:
        """
        Used to determine where to build the page.
        Returns a path string, relative to settings.BUILD_DIR.
        """
        url_part = self.get_url(obj)
        if url_part is None:  # Should ideally be caught by ImproperlyConfigured in get_url
            raise ImproperlyConfigured(
                f"get_url() returned None for object {obj}. "
                "Ensure get_absolute_url() is implemented correctly "
                "or get_url() is overridden.",
            )

        # Ensure url_part is a string before calling lstrip
        if not isinstance(url_part, str):
            raise ImproperlyConfigured(
                f"get_url() for object {obj} did not return a string (got {type(url_part)}). "
                "Ensure it returns a valid URL path.",
            )

        url_part_stripped = url_part.lstrip("/")
        target_path = Path(url_part_stripped)

        # If the view itself has a `build_path` attribute, it's used as a prefix directory.
        # Example: self.build_path = "items/", url_part = "my-object/"
        #          target_path becomes "items/my-object/"
        if hasattr(self, "build_path") and self.build_path is not None:
            # Ensure self.build_path is treated as a directory prefix
            prefix_path = Path(str(self.build_path).lstrip("/"))
            target_path = prefix_path / target_path

        # If the resulting path doesn't have a file extension (e.g., "items/my-object/"),
        # or explicitly ends with a slash, append "index.html".
        if not target_path.suffix or str(target_path).endswith("/"):
            return str(target_path / "index.html")

        return str(target_path)

    def set_kwargs(self, obj):
        """
        Sets the kwargs for the view based on the object.
        This is used to simulate the behavior of a DetailView
        when building the view.

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
        Builds a single detail page for the given object.
        """
        logger.debug(f"Building detail for object: {obj}")

        # Create a request object. The path for the request should be the
        # canonical URL of the object.
        self.request = self.create_request(self.get_url(obj))

        relative_file_path = self.get_build_path(obj)

        # Pass the 'obj' to get_content. This allows BuildableMixin.get_content
        # to set self.object, which our overridden self.get_object can then use,
        # bypassing the need for URL kwargs.
        content = self.get_content(obj=obj)

        self.build_file(relative_file_path, content)

    @property
    def build_method(self):
        """
        Specifies that building this view involves building its queryset.
        """
        return self.build_queryset

    def build_queryset(self):
        """
        Builds a detail page for each object in the queryset.
        """
        for o in self.get_queryset().all():
            self.build_object(o)

    def unbuild_object(self, obj):
        """
        Deletes the built detail page for the given object.
        """
        logger.debug(f"Unbuilding detail for object: {obj}")
        relative_file_path = self.get_build_path(obj)

        # Debugging for the 'unbuild_file' AttributeError
        if not hasattr(self, "unbuild_file"):  # pragma: no cover
            logger.error(
                f"CRITICAL: {self.get_class_name()} instance does not have 'unbuild_file' method.",
            )
            logger.error(f"MRO for {self.get_class_name()}: {self.__class__.mro()}")
            logger.error(f"Attributes of self: {dir(self)}")
            # Potentially raise an error here or skip if unbuild_file is critical
            # For now, let's proceed, and the AttributeError will be raised if it's truly missing.

        self.unbuild_file(relative_file_path)
