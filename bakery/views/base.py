#!/usr/bin/env python
"""
Views that inherit from Django's class-based generic views and add methods
for building flat files.
"""

import gzip
import logging
import mimetypes
from pathlib import Path  # Import Path

import six  # six is a Python 2 and 3 compatibility library
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest
from django.test.client import RequestFactory
from django.views.generic import RedirectView, TemplateView

# Note: DEFAULT_GZIP_CONTENT_TYPES and get_s3_client imports are moved into
# methods
# to potentially avoid circular import issues during Django setup.


logger = logging.getLogger(__name__)


class BuildableMixin:
    """
    Common methods we will use in buildable views.
    """

    build_path: str | None = None  # For views that build a single, fixed path

    def get_class_name(self):
        """
        Returns the class name of the view.
        """
        return self.__class__.__name__

    def create_request(self, path: str) -> HttpRequest:
        """
        Returns a GET request object for use when building views.
        """
        return RequestFactory().get(path)

    def get_content(self, obj=None) -> bytes:
        """
        How to render the HTML or other content for the page.
        Ensures self.request is set and content is returned as bytes.
        """
        if obj:
            self.object = obj

        if not hasattr(self, "request") or self.request is None:
            req_path = "/"
            # Try to determine a sensible request path
            if obj and hasattr(self, "get_url"):
                try:
                    req_path = self.get_url(obj)
                except Exception:  # Broad except if get_url(obj) fails
                    # Fallback if get_url(obj) fails or view doesn't need obj for URL
                    if hasattr(self, "get_url") and not obj:
                        try:
                            req_path = self.get_url()
                        except Exception:  # Broad except if get_url() fails
                            pass  # req_path remains "/" or previous value
                    elif hasattr(self, "build_path") and self.build_path:
                        req_path = self.build_path
            elif hasattr(self, "build_path") and self.build_path:
                req_path = self.build_path
            elif hasattr(self, "get_url"):  # For views that don't take obj in get_url
                try:
                    req_path = self.get_url()
                except TypeError:  # If get_url expects an obj this view doesn't have context for
                    logger.warning(
                        f"Could not determine request path for "
                        f"{self.get_class_name()} via get_url(). Defaulting to '/'.",
                    )
                    pass  # req_path remains "/"

            self.request = self.create_request(req_path)

        rendered_content = self.get(self.request).render().content
        if isinstance(rendered_content, str):
            return rendered_content.encode("utf-8")
        return rendered_content

    def prep_directory(self, target_dir_relative: str):  # DEPRECATED
        logger.warning(
            "BuildableMixin.prep_directory is deprecated. "
            "Directory creation is handled by write_file/gzip_file.",
        )

    def build_file(self, relative_path: str, content_data: bytes):
        """
        Writes out the provided content_data to the provided relative_path.
        Handles gzipping if applicable.
        """
        if self.is_gzippable(relative_path):
            self.gzip_file(relative_path, content_data)
        else:
            self.write_file(relative_path, content_data)

    def write_file(self, target_path_relative: str, content_bytes: bytes):
        """
        Writes out the provided bytes to the provided relative path.
        Ensures parent directories are created.
        """
        target_file_path = Path(settings.BUILD_DIR) / target_path_relative
        logger.debug(f"Building to {target_file_path}")
        try:
            target_file_path.parent.mkdir(parents=True, exist_ok=True)
            with target_file_path.open("wb") as outfile:
                outfile.write(content_bytes)
        except Exception as e:
            logger.error(f"Failed to write file {target_file_path}: {e}", exc_info=True)
            raise

    def is_gzippable(self, path: str) -> bool:
        """
        Returns a boolean indicating if the provided file path is a candidate
        for gzipping.
        """
        from bakery import DEFAULT_GZIP_CONTENT_TYPES  # Local import

        if not getattr(settings, "BAKERY_GZIP", False):
            return False
        whitelist = getattr(settings, "GZIP_CONTENT_TYPES", DEFAULT_GZIP_CONTENT_TYPES)
        guessed_type, _ = mimetypes.guess_type(path)
        return guessed_type in whitelist if guessed_type else False

    def gzip_file(self, target_path_relative: str, content_bytes: bytes):
        """
        Zips up the provided content_bytes as a companion for the provided
        relative path. Ensures parent directories are created.
        """
        target_file_path = Path(settings.BUILD_DIR) / target_path_relative
        logger.debug(f"Gzipping to {target_file_path}")
        try:
            target_file_path.parent.mkdir(parents=True, exist_ok=True)
            data_buffer = six.BytesIO()
            # Use the original filename for the GZip header for consistency
            kwargs = dict(filename=target_file_path.name, mode="wb", fileobj=data_buffer, mtime=0)
            with gzip.GzipFile(**kwargs) as f:
                f.write(content_bytes)
            with target_file_path.open("wb") as outfile:
                outfile.write(data_buffer.getvalue())
        except Exception as e:
            logger.error(f"Failed to gzip file {target_file_path}: {e}", exc_info=True)
            raise

    def get_build_path(self, obj=None) -> str:
        """
        Return the path to the file that will be built, relative to BUILD_DIR.
        If `obj` is provided, it's typically for object-specific pages.
        This method MUST be overridden by views that build
        multiple object pages or views that have a dynamic build path for objects.
        For simple views building a single page (obj=None), `self.build_path` is used.
        """
        if obj is not None:
            # Subclasses like BuildableDetailView or date archive views MUST implement this
            raise NotImplementedError(
                f"{self.get_class_name()} received an object but its "
                "get_build_path method does not handle it. "
                "Override get_build_path(self, obj).",
            )

        # For obj=None case (single page views like BuildableTemplateView)
        if self.build_path is None:
            raise NotImplementedError(
                f"{self.get_class_name()} must define a 'build_path' "
                f"attribute "
                "or an overridden 'get_build_path' method that handles "
                "obj=None.",
            )
        return str(self.build_path).lstrip("/")

    def unbuild_file(self, path_to_file: str):
        """
        Deletes the file at the provided path.
        'path_to_file' is expected to be a path string relative to
        settings.BUILD_DIR.
        """
        full_path = Path(settings.BUILD_DIR) / path_to_file
        if full_path.exists() and full_path.is_file():
            logger.debug(f"Deleting {full_path}")
            try:
                full_path.unlink()
            except Exception as e:
                logger.error(f"Failed to delete file {full_path}: {e}", exc_info=True)
        elif full_path.exists():
            logger.warning(
                f"Attempted to delete file {full_path}, but it is not a file (e.g., a directory).",
            )
        else:
            logger.debug(f"File {full_path} does not exist. Nothing to unbuild.")

    @property
    def build_method(self):
        """
        Returns the method that should be called to build the view.
        """
        if hasattr(self, "build_queryset"):  # For views building multiple objects
            return self.build_queryset
        elif hasattr(self, "build_page"):  # For views building a single page based on self
            return self.build_page
        # Fallback to a 'build' method if defined directly on the class
        # (e.g., BuildableTemplateView.build)
        elif callable(getattr(self, "build", None)) and self.build != self.build:
            # Ensure it's not pointing back to this BuildableMixin.build to avoid recursion
            # if a subclass defines build() and also inherits this.
            # This condition is tricky; usually subclasses explicitly define build_method
            # or their build() calls build_page() or build_queryset().
            # For now, if 'build' exists and is callable, assume it's the intended method.
            # Subclasses like BuildableTemplateView override build() to call build_page().
            return self.build
        raise NotImplementedError(
            f"{self.get_class_name()} requires a 'build_method' property "
            "that points to the correct build function (e.g., build_queryset, "
            "build_page, or a custom build method).",
        )

    def build(self):
        """
        A generic build method. Tries to infer the correct one via
        build_method property.
        Subclasses like BuildableTemplateView override this to call their specific logic.
        """
        build_func = self.build_method
        build_func()

    def unbuild(self):
        """
        Deletes the file(s) built by this view (for single-page views).
        """
        try:
            relative_path = self.get_build_path()  # Call without obj
            self.unbuild_file(relative_path)
        except (NotImplementedError, AttributeError) as e:
            logger.warning(
                f"Could not unbuild {self.get_class_name()} using default "
                f"unbuild logic "
                f"(likely a multi-object view or get_build_path needs "
                f"obj=None handling): {e}",
            )

    def build_page(self):
        """
        Builds a single page. Assumes get_build_path (without obj) and
        get_content (without obj, or self.object is already set)
        can be called or rely on view attributes.
        """
        logger.debug(f"Building single page for {self.get_class_name()}")
        req_path = "/"
        try:
            # For single page views, get_build_path() should not require an object
            req_path = self.get_build_path()
        except (NotImplementedError, TypeError) as e:
            logger.warning(
                f"Could not determine request path for build_page on {self.get_class_name()} "
                f"via get_build_path (Error: {e}). Trying get_url if available.",
            )
            if hasattr(self, "get_url"):
                try:
                    req_path = self.get_url()
                except TypeError:  # If get_url also needs obj
                    logger.warning(
                        f"get_url for {self.get_class_name()} also needs an "
                        f"object. Defaulting request path to '/'.",
                    )
            else:
                logger.warning("No get_url method. Defaulting request path to '/'.")

        self.request = self.create_request(req_path)
        relative_file_path = (
            self.get_build_path()
        )  # Should be the same as req_path for simple views
        self.build_file(
            relative_file_path,
            self.get_content(),
        )  # get_content might use self.object if set

    def unbuild_object(self, obj):
        """
        Deletes the built page for a specific object.
        This is intended for views that build pages on a per-object basis,
        like detail views.
        """
        logger.debug(f"Unbuilding page for object: {obj} using view {self.get_class_name()}")
        try:
            # Assumes get_build_path(obj) is implemented by the subclass
            relative_file_path = self.get_build_path(obj)
            self.unbuild_file(relative_file_path)
        except (NotImplementedError, AttributeError, ImproperlyConfigured) as e:
            logger.error(
                f"Failed to unbuild object {obj} with view "
                f"{self.get_class_name()}. "
                f"Could not determine build path or unbuild_file failed: {e}",
                exc_info=True,
            )


class BuildableTemplateView(TemplateView, BuildableMixin):
    """
    Renders and builds a simple template.
    (Docstring continues...)
    """

    build_path: str  # Make it explicit that this is expected

    @property
    def build_method(self):
        # This view's build logic is encapsulated in its own build() method,
        # which then calls build_page().
        return self.build

    def build(self):  # Overrides BuildableMixin.build
        logger.debug(
            f"BuildableTemplateView: Building {self.template_name} to {self.get_build_path()}",
        )
        # Calls the build_page method from BuildableMixin
        self.build_page()

    def get_build_path(self) -> str:  # Overrides BuildableMixin.get_build_path for obj=None case
        """
        Returns the build_path, ensuring it's a relative path string.
        This version is for views that build a single, fixed path.
        """
        if not hasattr(self, "build_path") or not self.build_path:
            raise NotImplementedError(
                f"{self.get_class_name()} must define a 'build_path' attribute.",
            )
        return str(self.build_path).lstrip("/")


class Buildable404View(BuildableTemplateView):
    """
    The default Django 404 page, but built out.
    """

    build_path = "404.html"
    template_name = "404.html"


class BuildableRedirectView(RedirectView, BuildableMixin):
    """
    Render and build a redirect.
    (Docstring continues...)
    """

    build_path: str  # Make it explicit
    permanent = True

    def get_content(self) -> bytes:
        """
        Generates the HTML content for the redirect.
        Ensures self.request is set before calling get_redirect_url.
        """
        if not hasattr(self, "request") or self.request is None:
            # The request path should be the path of the redirecting file itself
            self.request = self.create_request(self.get_build_path())

        redirect_url = self.get_redirect_url()  # Relies on self.request
        if redirect_url is None:
            logger.error(f"Could not determine redirect URL for {self.build_path}")
            return b"<html><body>Could not determine redirect URL.</body></html>"

        html = f"""
        <html>
            <head>
            <meta http-equiv="Refresh" content="0;url={redirect_url}" />
            </head>
            <body></body>
        </html>
        """
        return html.strip().encode("utf-8")

    @property
    def build_method(self):
        # This view's build logic is encapsulated in its own build() method.
        return self.build

    def build(self):  # Overrides BuildableMixin.build
        # 1. Determine the build path for the redirect file itself
        relative_build_path = self.get_build_path()

        # 2. Create a request object for this path. This is needed by get_redirect_url()
        #    and subsequently by get_content().
        self.request = self.create_request(relative_build_path)

        # 3. Determine the target URL for the redirect (uses self.request)
        redirect_url = self.get_redirect_url()
        logger.debug(
            f"BuildableRedirectView: Building redirect from "
            f"{relative_build_path} to {redirect_url}",
        )

        # 4. Get the HTML content for the redirect (uses self.request via get_redirect_url)
        content_for_file = self.get_content()

        # 5. Build the file
        self.build_file(relative_build_path, content_for_file)

    def get_build_path(self) -> str:  # Overrides BuildableMixin.get_build_path for obj=None case
        """
        Returns the build_path, ensuring it's a relative path string.
        """
        if not hasattr(self, "build_path") or not self.build_path:
            raise NotImplementedError(
                f"{self.get_class_name()} must define a 'build_path' attribute.",
            )
        return str(self.build_path).lstrip("/")

    # get_redirect_url is inherited from Django's RedirectView

    def post_publish(self, bucket_name: str):
        """
        Sets the S3 redirect header on the published file.
        `bucket_name` is the name of the S3 bucket.
        """
        from bakery.management.commands import get_s3_client  # Local import

        # Ensure self.request is set if get_redirect_url relies on it
        if not hasattr(self, "request") or self.request is None:
            self.request = self.create_request(self.get_build_path())

        redirect_url = self.get_redirect_url()
        if redirect_url is None:
            logger.error(f"Cannot set S3 redirect for {self.build_path}: redirect URL is None.")
            return

        s3_key = self.get_build_path()  # The key in S3 should be the relative build path
        logger.debug(
            f"Adding S3 redirect header for {s3_key} in bucket {bucket_name} to {redirect_url}",
        )
        s3_client, _ = get_s3_client()
        try:
            s3_client.copy_object(
                ACL="public-read",
                Bucket=bucket_name,
                CopySource={
                    "Bucket": bucket_name,
                    "Key": s3_key,
                },
                Key=s3_key,
                WebsiteRedirectLocation=redirect_url,
                MetadataDirective="REPLACE",  # Important when setting WebsiteRedirectLocation
            )
        except Exception as e:
            logger.error(f"Failed to set S3 redirect for {s3_key}: {e}", exc_info=True)
