"""
Views that inherit from Django's class-based generic views and add methods
for building flat files.
"""

import gzip
import io
import logging
import mimetypes
import posixpath
import re
from collections.abc import Callable
from os import PathLike
from typing import BinaryIO, Protocol, cast

from django.apps import apps
from django.conf import settings
from django.http import HttpRequest
from django.test.client import RequestFactory
from django.urls import NoReverseMatch, reverse
from django.utils.encoding import smart_str
from django.views.generic import RedirectView, TemplateView

from bakery import DEFAULT_GZIP_CONTENT_TYPES
from bakery.filesystem import (
    RootedFilesystem,
    is_root_path,
    join_path,
    normalize_path,
)
from bakery.management.commands import get_s3_client

logger = logging.getLogger(__name__)


BuildPath = str | PathLike[str]


class _WritableFilesystem(Protocol):
    def exists(self, path: str) -> bool: ...

    def makedirs(self, path: str) -> None: ...

    def open(self, path: str, mode: str) -> BinaryIO: ...

    def removetree(self, path: str) -> None: ...


class _RenderedResponse(Protocol):
    content: bytes


class _TemplateRenderingView(Protocol):
    request: HttpRequest

    def get(
        self, request: HttpRequest, *args: object, **kwargs: object
    ) -> "_TemplateRenderingView": ...

    def render(self) -> _RenderedResponse: ...


class _S3Bucket(Protocol):
    name: str


class _S3Client(Protocol):
    def copy_object(self, **kwargs: object) -> object: ...


class BuildableMixin:
    """
    Common methods we will use in buildable views.
    """

    fs_name = cast("str", apps.get_app_config("bakery").filesystem_name)
    fs = cast("_WritableFilesystem", apps.get_app_config("bakery").filesystem)

    def create_request(self, path: BuildPath) -> HttpRequest:
        """
        Returns a GET request object for use when building views.

        If inheriting views require additional request attributes
        (e.g. user, site), override this method and define those
        attributes on the returned object.
        """
        return cast("HttpRequest", RequestFactory().get(str(path)))

    def get_content(self) -> bytes:
        """
        How to render the HTML or other content for the page.

        If you choose to render using something other than a Django template,
        like HttpResponse for instance, you will want to override this.
        """
        view = cast("_TemplateRenderingView", self)
        return view.get(view.request).render().content

    def prep_directory(self, target_dir: BuildPath) -> None:
        """
        Prepares the parent directory for a BUILD_DIR-relative output path.
        """
        self._prep_output_directory(self.get_output_path(target_dir))

    def _prep_output_directory(self, output_path: str) -> None:
        """Prepare the parent directory for an already resolved output path."""
        dirname = posixpath.dirname(output_path)
        if dirname and not self.fs.exists(dirname):
            logger.debug("Creating directory at %s%s", self.fs_name, dirname)
            self.fs.makedirs(dirname)

    def get_output_path(self, build_path: BuildPath) -> str:
        """Return a normalized path contained by the configured build directory."""
        build_dir = normalize_path(cast("BuildPath", settings.BUILD_DIR))
        raw_path = str(build_path).replace("\\", "/")
        if re.fullmatch(r"[A-Za-z]:.*", raw_path):
            raise ValueError("Build path must remain within BUILD_DIR.")
        raw_segments = raw_path.split("/")
        if ".." in raw_segments:
            raise ValueError("Build path must remain within BUILD_DIR.")
        normalized_path = normalize_path(build_path)
        relative_path = normalized_path.lstrip("/")
        if (
            isinstance(self.fs, RootedFilesystem)
            and not self.fs.root
            and is_root_path(build_dir)
        ):
            raise ValueError("BUILD_DIR must not target an unrooted filesystem root.")
        if build_dir in {".", "/", "//"}:
            return relative_path
        return join_path(build_dir, relative_path)

    def build_file(self, target_path: BuildPath, html: bytes) -> None:
        if self.is_gzippable(target_path):
            self.gzip_file(target_path, html)
        else:
            self.write_file(target_path, html)

    def write_file(self, target_path: BuildPath, html: bytes) -> None:
        """
        Writes out the provided HTML to the provided path.
        """
        logger.debug("Building to %s%s", self.fs_name, target_path)
        with self.fs.open(smart_str(target_path), "wb") as outfile:
            outfile.write(html)

    def is_gzippable(self, target_path: BuildPath) -> bool:
        """
        Returns a boolean indicating if the provided file path is a candidate
        for gzipping.
        """
        # First check if gzipping is allowed by the global setting
        if not getattr(settings, "BAKERY_GZIP", False):
            return False
        # Then check if the content type of this particular file is gzippable
        whitelist = getattr(settings, "GZIP_CONTENT_TYPES", DEFAULT_GZIP_CONTENT_TYPES)
        return mimetypes.guess_type(str(target_path))[0] in whitelist

    def gzip_file(self, target_path: BuildPath, html: bytes) -> None:
        """
        Zips up the provided HTML as a companion for the provided path.

        Intended to take advantage of the peculiarities of
        Amazon S3's GZIP service.

        mtime, an option that writes a timestamp to the output file
        is set to 0, to avoid having s3cmd do unnecessary uploads because
        of differences in the timestamp
        """
        logger.debug("Gzipping to %s%s", self.fs_name, target_path)

        # Write GZIP data to an in-memory buffer
        data_buffer = io.BytesIO()
        with gzip.GzipFile(
            filename=posixpath.basename(str(target_path)),
            mode="wb",
            fileobj=data_buffer,
            mtime=0,
        ) as f:
            f.write(html)

        # Write that buffer out to the filesystem
        with self.fs.open(smart_str(target_path), "wb") as outfile:
            outfile.write(data_buffer.getvalue())


class BuildableTemplateView(TemplateView, BuildableMixin):
    """
    Renders and builds a simple template.

    When inherited, the child class should include the following attributes.

        build_path:
            The target location of the built file in the BUILD_DIR.
            `index.html` would place it at the built site's root.
            `foo/index.html` would place it inside a subdirectory.

        template_name:
            The name of the template you would like Django to render.
    """

    build_path: BuildPath

    @property
    def build_method(self) -> Callable[[], None]:
        return self.build

    def build(self) -> None:
        logger.debug("Building %s", self.template_name)
        build_path = self.get_build_path()
        self.request = self.create_request(build_path)
        output_path = self.get_output_path(build_path)
        self.prep_directory(build_path)
        self.build_file(output_path, self.get_content())

    def get_build_path(self) -> str:
        return normalize_path(self.build_path).lstrip("/")


class Buildable404View(BuildableTemplateView):
    """
    The default Django 404 page, but built out.
    """

    build_path = "404.html"
    template_name = "404.html"


class BuildableRedirectView(RedirectView, BuildableMixin):
    """
    Render and build a redirect.

    Required attributes:

        build_path:
            The URL being requested, which will be published as a flatfile
            with a redirect away from it.

        url:
            The URL where redirect will send the user. Operates
            in the same way as the standard generic RedirectView.
    """

    permanent = True
    build_path: BuildPath
    url: str | None
    pattern_name: str | None

    def get_content(self) -> bytes:
        html = """
        <html>
            <head>
            <meta http-equiv="Refresh" content="1;url=%s" />
            </head>
            <body></body>
        </html>
        """
        html = html % self.get_redirect_url()
        return html.encode("utf-8")

    @property
    def build_method(self) -> Callable[[], None]:
        return self.build

    def build(self) -> None:
        logger.debug(
            "Building redirect from %s to %s", self.build_path, self.get_redirect_url()
        )
        build_path = normalize_path(self.build_path).lstrip("/")
        self.request = self.create_request(build_path)
        output_path = self.get_output_path(build_path)
        self.prep_directory(build_path)
        self.build_file(output_path, self.get_content())

    def get_redirect_url(self, *args: object, **kwargs: object) -> str | None:
        """
        Return the URL redirect to. Keyword arguments from the
        URL pattern match generating the redirect request
        are provided as kwargs to this method.
        """
        if self.url:
            url = self.url % kwargs
        elif self.pattern_name:
            try:
                url = cast("str", reverse(self.pattern_name, args=args, kwargs=kwargs))
            except NoReverseMatch:
                return None
        else:
            return None
        return url

    def post_publish(self, bucket: _S3Bucket) -> None:
        build_path = str(self.build_path)
        logger.debug(
            "Adding S3 redirect header from %s to in %s to %s",
            build_path,
            bucket.name,
            self.get_redirect_url(),
        )
        s3_client, _s3_resource = cast("tuple[_S3Client, object]", get_s3_client())
        s3_client.copy_object(
            ACL="public-read",
            Bucket=bucket.name,
            CopySource={"Bucket": bucket.name, "Key": build_path},
            Key=build_path,
            # External redirects are an explicit feature of BuildableRedirectView.
            WebsiteRedirectLocation=self.get_redirect_url(),  # lgtm[py/url-redirection]
        )
