import logging
import shutil  # For shutil.rmtree and shutil.copytree
import tempfile
from pathlib import Path  # Import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

# from django.urls import get_callable # Not directly used in this refactor,
# but often useful
from django.utils.module_loading import import_string

# bakery import
from bakery.views import BuildableMixin

# from bakery import utils # If utils uses fs, it might need changes too

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Builds a static version of the site."
    # build_dir_path will store the Path object for the build directory
    build_dir_path: Path
    # static_root_path will store the Path object for STATIC_ROOT
    static_root_path: Path | None
    # media_root_path will store the Path object for MEDIA_ROOT
    media_root_path: Path | None

    def add_arguments(self, parser):
        parser.add_argument(
            "--build-dir",
            action="store",
            dest="build_dir",
            default="",  # Default will be handled by settings or tempdir
            help="Specify the directory where the built site will be saved.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            dest="clear",
            default=False,
            help="Clear the build directory before building.",
        )
        # Add any other arguments django-bakery's build command has, e.g.,
        # --skip-static, --skip-media

    def handle(self, *args, **options):
        logger.info("Build started")

        # Determine the build directory
        # Priority: command-line arg, settings.BUILD_DIR, then temp dir
        build_dir_override = options.get("build_dir")
        if build_dir_override:
            self.build_dir_path = Path(build_dir_override).resolve()
        elif hasattr(settings, "BUILD_DIR") and settings.BUILD_DIR:
            # Assuming settings.BUILD_DIR is a string path
            self.build_dir_path = Path(settings.BUILD_DIR).resolve()
        else:
            # Fallback to a temporary directory
            # tempfile.mkdtemp() returns an absolute path string
            self.build_dir_path = Path(tempfile.mkdtemp()).resolve()
            logger.info(
                f"No build directory specified, using temporary directory:"
                f" {self.build_dir_path}",
            )

        logger.info(f"Initializing build directory at {self.build_dir_path}")

        # Handle clearing and creation of the build directory
        self.setup_build_directory(clear=options.get("clear", False))

        # Get and prepare STATIC_ROOT and MEDIA_ROOT as Path objects
        if hasattr(settings, "STATIC_ROOT") and settings.STATIC_ROOT:
            self.static_root_path = Path(settings.STATIC_ROOT).resolve()
        else:
            self.static_root_path = None
            logger.warning("settings.STATIC_ROOT is not configured.")

        if hasattr(settings, "MEDIA_ROOT") and settings.MEDIA_ROOT:
            self.media_root_path = Path(settings.MEDIA_ROOT).resolve()
        else:
            self.media_root_path = None
            logger.warning("settings.MEDIA_ROOT is not configured.")

        # Build static files
        # Add skip options if you have them, e.g., if not options.get(
        # 'skip_static'):
        self.build_static()

        # Build media files
        # Add skip options, e.g., if not options.get('skip_media'):
        self.build_media()

        # Build views
        self.build_views()

        logger.info(f"Build finished. Site built in {self.build_dir_path}")

    def setup_build_directory(self, clear: bool = False):
        """
        Sets up the build directory. Clears it if specified and exists,
        then ensures it exists.
        """
        if self.build_dir_path.exists():
            if clear:
                logger.info(
                    f"Clearing existing build directory: {self.build_dir_path}",
                )
                try:
                    shutil.rmtree(self.build_dir_path)
                    # Recreate the directory after clearing
                    self.build_dir_path.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    raise CommandError(
                        f"Failed to clear build directory" f" {self.build_dir_path}: {e}",
                    ) from e
            # else: directory exists, and we're not clearing it
        else:
            logger.info(f"Creating build directory: {self.build_dir_path}")
            try:
                self.build_dir_path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise CommandError(
                    f"Failed to create build directory {self.build_dir_path}:" f" {e}",
                ) from e

    def build_static(self):
        """
        Copies files from STATIC_ROOT to the build directory.
        """
        if not self.static_root_path:
            logger.warning(
                "STATIC_ROOT not configured as a Path object. Skipping static " "files.",
            )
            return
        if not settings.STATIC_URL:
            logger.warning(
                "settings.STATIC_URL not configured. Skipping static files.",
            )
            return

        # Determine the target path within the build directory
        # e.g., if STATIC_URL is '/static/', target_name will be 'static'
        target_name = settings.STATIC_URL.strip("/")
        if not target_name:  # Handle case where STATIC_URL might be just "/"
            logger.warning(
                "STATIC_URL is '/' or empty, cannot determine static target "
                "directory name. Skipping static files.",
            )
            return
        static_build_target_path = self.build_dir_path / target_name

        if self.static_root_path.exists() and self.static_root_path.is_dir():
            logger.info(
                f"Building static directory at {static_build_target_path}",
            )

            # shutil.copytree requires the destination to not exist,
            # or dirs_exist_ok=True (Python 3.8+)
            if static_build_target_path.exists():
                logger.debug(
                    f"Removing existing static target directory:" f" {static_build_target_path}",
                )
                shutil.rmtree(static_build_target_path)

            logger.debug(
                f"Copying {self.static_root_path} to" f" {static_build_target_path}",
            )
            try:
                shutil.copytree(
                    self.static_root_path,
                    static_build_target_path,
                    dirs_exist_ok=True,
                )
            except Exception as e:
                logger.error(
                    f"Error copying static files from {self.static_root_path} "
                    f"to {static_build_target_path}: {e}",
                )
        else:
            logger.warning(
                f"STATIC_ROOT directory {self.static_root_path} does not "
                f"exist or is not a directory. Skipping static files.",
            )

    def build_media(self):
        """
        Copies files from MEDIA_ROOT to the build directory.
        """
        if not self.media_root_path:
            logger.warning(
                "MEDIA_ROOT not configured as a Path object. Skipping media " "files.",
            )
            return
        if not settings.MEDIA_URL:
            logger.warning(
                "settings.MEDIA_URL not configured. Skipping media files.",
            )
            return

        target_name = settings.MEDIA_URL.strip("/")
        if not target_name:
            logger.warning(
                "MEDIA_URL is '/' or empty, cannot determine media target "
                "directory name. Skipping media files.",
            )
            return
        media_build_target_path = self.build_dir_path / target_name

        if self.media_root_path.exists() and self.media_root_path.is_dir():
            logger.info(
                f"Building media directory at {media_build_target_path}",
            )

            if media_build_target_path.exists():
                logger.debug(
                    f"Removing existing media target directory:" f" {media_build_target_path}",
                )
                shutil.rmtree(media_build_target_path)

            logger.debug(
                f"Copying {self.media_root_path} to {media_build_target_path}",
            )
            try:
                shutil.copytree(
                    self.media_root_path,
                    media_build_target_path,
                    dirs_exist_ok=True,
                )
            except Exception as e:
                logger.error(
                    f"Error copying media files from {self.media_root_path} "
                    f"to {media_build_target_path}: {e}",
                )
        else:
            logger.warning(
                f"MEDIA_ROOT directory {self.media_root_path} does not exist "
                f"or is not a directory. Skipping media files.",
            )

    def get_build_path(self, view_path_str: str) -> Path:
        """
        Constructs the full path for a view's output file within the build
        directory. Ensures that 'index.html' is appended if the path ends
        with a slash or has no extension.
        """
        # Sanitize and prepare the path string
        path_str = view_path_str.lstrip("/")

        # Create a Path object to easily check for suffix and manipulate
        temp_path = Path(path_str)

        if not path_str or path_str.endswith("/"):
            # If path is empty or ends with a slash, it's a directory index
            path_str += "index.html"
        elif (
            not temp_path.suffix and temp_path.name
        ):  # No extension, and it's not just an empty string
            # If there's no file extension, assume it's a directory and
            # append /index.html
            path_str += "/index.html"

        return self.build_dir_path / path_str

    def build_views(self):
        """
        Builds all views defined in BAKERY_VIEWS.
        """
        if not hasattr(settings, "BAKERY_VIEWS"):
            raise CommandError(
                "BAKERY_VIEWS setting not found. Please define it in your " "settings.",
            )

        for view_str in settings.BAKERY_VIEWS:
            logger.debug(f"Attempting to build view: {view_str}")
            try:
                view_class = import_string(view_str)
            except ImportError as e:
                logger.error(f"Error importing view '{view_str}': {e}")
                continue

            if not issubclass(view_class, BuildableMixin):
                logger.error(
                    f"View '{view_str}' does not inherit from "
                    f"bakery.views.BuildableMixin. Skipping.",
                )
                continue

            view_instance = view_class()

            items_to_build = []
            try:
                if hasattr(view_instance, "build_queryset") and callable(
                    view_instance.build_queryset,
                ):
                    queryset = view_instance.build_queryset()
                    if queryset is not None:
                        items_to_build.extend(list(queryset))
                elif hasattr(view_instance, "get_build_obj_list") and callable(
                    view_instance.get_build_obj_list,
                ):
                    items_to_build.extend(view_instance.get_build_obj_list())
                else:
                    # Assumed to be a single page view or get_path doesn't
                    # need an object
                    items_to_build.append(None)
            except Exception as e:
                logger.error(
                    f"Error getting items to build from view '{view_str}': {e}",
                    exc_info=True,
                )
                continue

            for item in items_to_build:
                item_repr = repr(item) if item else "default item"
                try:
                    current_url = view_instance.get_path(item) if item else view_instance.get_path()

                    # Content generation logic:
                    # This needs to be robust and handle different view types.
                    # The original bakery often uses a test client.
                    # For Wagtail, direct page rendering is common.
                    content = None
                    output_path_override = None  # For views that specify their exact output path

                    if hasattr(view_instance, "build_file") and callable(
                        view_instance.build_file,
                    ):
                        # This method is expected to return (path_str,
                        # content_bytes)
                        # path_str could be relative to build_dir or absolute
                        path_info, content = view_instance.build_file(
                            self.build_dir_path,
                            item,
                        )
                        output_path_override = Path(path_info)
                        if not output_path_override.is_absolute():
                            output_path_override = self.build_dir_path / output_path_override

                    elif (
                        hasattr(item, "serve") and callable(item.serve) and hasattr(item, "get_url")
                    ):  # Wagtail Page
                        from django.test import (  # Local import to avoid;;; dependency if not used
                            RequestFactory,
                        )

                        factory = RequestFactory()
                        # Use page's actual URL for context, but ensure it's
                        # a simple path for the fake request
                        page_url_path = item.get_url() or "/"
                        fake_request = factory.get(page_url_path)
                        # Add user to request if your page rendering depends
                        # on it
                        # if hasattr(settings, 'ANONYMOUS_USER_ID'):
                        #     from django.contrib.auth import get_user_model
                        #     User = get_user_model()
                        #     fake_request.user = User.objects.get(
                        #     pk=settings.ANONYMOUS_USER_ID)
                        # else:
                        #     from django.contrib.auth.models import
                        #     AnonymousUser
                        #     fake_request.user = AnonymousUser()

                        response = item.serve(fake_request)
                        if hasattr(response, "render") and callable(
                            response.render,
                        ):  # Render if it's a TemplateResponse
                            response.render()
                        content = response.content

                    # Add more elif branches here for other view types or
                    # custom build methods
                    # e.g., using Django Test Client for generic Django views
                    # elif isinstance(view_instance, (View, TemplateView,
                    # ListView, DetailView)):
                    #     from django.test import Client
                    #     client = Client()
                    #     response = client.get(current_url) # This might
                    #     need kwargs for DetailView
                    #     if response.status_code == 200:
                    #         content = response.content
                    #     else:
                    #         logger.warning(f"View {view_str} for {
                    #         item_repr} returned status {
                    #         response.status_code} at {current_url}")
                    #         continue

                    else:
                        logger.warning(
                            f"No specific content generation method found for "
                            f"view '{view_str}' with item {item_repr}. "
                            f"Skipping.",
                        )
                        continue

                    if content is None:
                        logger.warning(
                            f"Content for view '{view_str}' with item"
                            f" {item_repr} was None. Skipping.",
                        )
                        continue

                    # Determine output file path
                    output_path = (
                        output_path_override
                        if output_path_override
                        else self.get_build_path(current_url)
                    )

                    logger.debug(f"Building {output_path} for item {item_repr}")

                    # Ensure parent directory exists
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    # Write the content
                    with output_path.open(
                        "wb",
                    ) as f:  # Open in binary mode for bytes content
                        f.write(content)

                except Exception as e:
                    err_url = current_url if "current_url" in locals() else "N/A"
                    logger.error(
                        f"Error building page for view '{view_str}' with item"
                        f" {item_repr} (URL: {err_url}): {e}",
                        exc_info=True,
                    )
                    # Optionally, re-raise or continue based on desired
                    # strictness
                    # raise CommandError(f"Failed to build {view_str}: {e}")
                    continue  # Continue with the next item/view
