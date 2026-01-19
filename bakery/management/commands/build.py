# C:/dev/git_clones/django-bakery/bakery/management/commands/build.py
import logging
import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management import call_command  # <<< ADD THIS IMPORT
from django.core.management.base import BaseCommand, CommandError
from django.utils.module_loading import import_string

from bakery.views import BuildableMixin

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Builds a static version of the site."
    build_dir_path: Path
    static_root_path: Path | None
    media_root_path: Path | None

    def add_arguments(self, parser):
        parser.add_argument(
            "--build-dir",
            action="store",
            dest="build_dir",
            default="",
            help="Specify the directory where the built site will be saved.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            dest="clear",
            default=False,
            help="Clear the build directory before building.",
        )
        # Add arguments for skipping static/media if desired, and verbosity for collectstatic
        parser.add_argument(
            "--skip-static",
            action="store_true",
            help="Skip collecting and building static files.",
        )
        parser.add_argument(
            "--skip-media",
            action="store_true",
            help="Skip copying media files.",
        )
        parser.add_argument(
            "--collectstatic-verbosity",
            action="store",
            type=int,
            # Removed default to let it inherit from main verbosity if not set
            help="Set verbosity level for collectstatic command (0-3).",
        )
        parser.add_argument(
            "--no-clear-static-root",  # Changed to be an opt-out of clearing
            action="store_false",
            dest="clear_static_root",  # Default to True (clear)
            default=True,
            help="Do not clear STATIC_ROOT before running collectstatic.",
        )

    def handle(self, *args, **options):
        logger.info("Build started")

        build_dir_override = options.get("build_dir")
        if build_dir_override:
            self.build_dir_path = Path(build_dir_override).resolve()
        elif hasattr(settings, "BUILD_DIR") and settings.BUILD_DIR:
            self.build_dir_path = Path(settings.BUILD_DIR).resolve()
        else:
            self.build_dir_path = Path(tempfile.mkdtemp()).resolve()
            logger.info(
                f"No build directory specified, using temporary directory: {self.build_dir_path}",
            )

        logger.info(f"Initializing build directory at {self.build_dir_path}")
        self.setup_build_directory(clear=options.get("clear", False))

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

        # Collect static files first (if not skipped)
        if not options.get("skip_static"):
            if self.static_root_path:
                # Determine verbosity for collectstatic
                # Priority: --collectstatic-verbosity, then main verbosity
                collectstatic_verbosity_level = options.get("collectstatic_verbosity")
                if collectstatic_verbosity_level is None:  # Not explicitly set
                    collectstatic_verbosity_level = options.get("verbosity")

                logger.info(
                    f"Running collectstatic (verbosity: {collectstatic_verbosity_level}, "
                    f"clear: {options.get('clear_static_root')})",
                )
                try:
                    call_command(
                        "collectstatic",
                        interactive=False,
                        verbosity=collectstatic_verbosity_level,
                        clear=options.get("clear_static_root"),  # Pass the clear option
                    )
                except Exception as e:
                    logger.error(f"Error during collectstatic: {e}", exc_info=True)
                    # Decide if this should be a CommandError
                    # raise CommandError(f"collectstatic failed: {e}")
                # After collectstatic, build_static will copy from STATIC_ROOT
                self.build_static()
            else:
                logger.warning(
                    "STATIC_ROOT not configured. Skipping static file collection and building.",
                )
        else:
            logger.info("Skipping static file collection and building as per --skip-static.")

        if not options.get("skip_media"):
            self.build_media()
        else:
            logger.info("Skipping media file copying as per --skip-media.")

        self.build_views()

        logger.info(f"Build finished. Site built in {self.build_dir_path}")

    def setup_build_directory(self, clear: bool = False):
        if self.build_dir_path.exists():
            if clear:
                logger.info(
                    f"Clearing existing build directory: {self.build_dir_path}",
                )
                try:
                    shutil.rmtree(self.build_dir_path)
                    self.build_dir_path.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    raise CommandError(
                        f"Failed to clear build directory {self.build_dir_path}: {e}",
                    ) from e
        else:
            logger.info(f"Creating build directory: {self.build_dir_path}")
            try:
                self.build_dir_path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise CommandError(
                    f"Failed to create build directory {self.build_dir_path}: {e}",
                ) from e

    def build_static(self):
        if not self.static_root_path:
            # This warning is now less critical if collectstatic is handled before
            logger.debug(
                "STATIC_ROOT not available for copying. Static files should "
                "have been handled by collectstatic.",
            )
            return
        if not settings.STATIC_URL:
            logger.warning(
                "settings.STATIC_URL not configured. Cannot determine static "
                "target in build directory.",
            )
            return

        target_name = settings.STATIC_URL.strip("/")
        if not target_name:
            logger.warning(
                "STATIC_URL is '/' or empty. Cannot determine static target directory name.",
            )
            return
        static_build_target_path = self.build_dir_path / target_name

        if self.static_root_path.exists() and self.static_root_path.is_dir():
            logger.info(f"Copying collected static files to {static_build_target_path}")
            if static_build_target_path.exists():
                logger.debug(
                    f"Removing existing static target directory: {static_build_target_path}",
                )
                shutil.rmtree(static_build_target_path)
            try:
                shutil.copytree(self.static_root_path, static_build_target_path, dirs_exist_ok=True)
            except Exception as e:
                logger.error(
                    f"Error copying static files from {self.static_root_path} "
                    f"to {static_build_target_path}: {e}",
                )
        else:
            logger.warning(
                f"STATIC_ROOT directory {self.static_root_path} does not "
                f"exist or is not a directory after collectstatic. Nothing to copy.",
            )

    # ... build_media and build_views methods remain the same ...
    def build_media(self):
        """
        Copies files from MEDIA_ROOT to the build directory.
        """
        if not self.media_root_path:
            logger.warning(
                "MEDIA_ROOT not configured as a Path object. Skipping media files.",
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
                    f"Removing existing media target directory: {media_build_target_path}",
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
                "BAKERY_VIEWS setting not found. Please define it in your settings.",
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
                    # For views like list views or detail views that operate on a queryset
                    # The build_queryset method itself should handle iterating and building
                    # For now, let's assume it might return a list of objects if the
                    # view's get_path needs an object.
                    # This part of the original bakery was a bit complex.
                    # Let's simplify: if build_queryset exists, we call it
                    # and assume it does the work.
                    # Or, it returns a list of objects for which get_path and
                    # get_content are called.
                    # The current structure of BuildableMixin views suggests
                    # build_queryset/build_method
                    # handles its own iteration and file writing.
                    # So, the loop below might be redundant if views build themselves fully.

                    # If the view's build_method (often build_queryset) handles everything:
                    if hasattr(view_instance, "build_method"):
                        logger.debug(f"Calling build_method for {view_str}")
                        view_instance.build_method()  # This view builds itself
                        continue  # Move to the next view in BAKERY_VIEWS
                    else:  # Fallback if no build_method, try to get a list
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
                    items_to_build.append(
                        None,
                    )  # Triggers one build iteration for single-page views
            except Exception as e:
                logger.error(
                    f"Error getting items to build from view '{view_str}': {e}",
                    exc_info=True,
                )
                continue

            # This loop is for views that return a list of items to build,
            # and the command orchestrates getting path and content for each.
            for item in items_to_build:
                item_repr = repr(item) if item else "default item (single page view)"
                try:
                    # Determine URL/path for the item
                    # Views should have a get_path(self, obj=None) or build_path attribute
                    current_url = None
                    if hasattr(view_instance, "get_path"):
                        current_url = (
                            view_instance.get_path(item) if item else view_instance.get_path()
                        )
                    elif hasattr(view_instance, "build_path"):  # For simple views with fixed path
                        current_url = view_instance.build_path
                        if callable(current_url):  # If build_path is a method
                            current_url = current_url(item) if item else current_url()

                    if not current_url:
                        logger.error(
                            f"Could not determine URL/path for view '"
                            f"{view_str}' with item {item_repr}. Skipping.",
                        )
                        continue

                    content = None
                    output_path_override = None

                    # How view_instance generates content and path:
                    # Option 1: view_instance.build_file(build_dir_path, item)
                    #  -> (output_path_str, content_bytes)
                    if hasattr(view_instance, "build_file") and callable(view_instance.build_file):
                        path_info, content_bytes = view_instance.build_file(
                            self.build_dir_path,
                            item,
                        )
                        output_path_override = Path(path_info)
                        if not output_path_override.is_absolute():
                            output_path_override = self.build_dir_path / output_path_override
                        content = content_bytes  # Already bytes

                    # Option 2: view_instance.get_content(item) -> content_bytes or content_str
                    elif hasattr(view_instance, "get_content") and callable(
                        view_instance.get_content,
                    ):
                        # Ensure request is set up if get_content needs it (common for Django views)
                        if not hasattr(view_instance, "request") or view_instance.request is None:
                            from django.test import RequestFactory

                            view_instance.request = RequestFactory().get(
                                current_url.lstrip("/") or "/",
                            )

                        content_data = (
                            view_instance.get_content(item) if item else view_instance.get_content()
                        )
                        if isinstance(content_data, str):
                            content = content_data.encode("utf-8")
                        elif isinstance(content_data, bytes):
                            content = content_data
                        else:
                            logger.error(
                                f"Content from get_content for {view_str} was "
                                f"not str or bytes. Skipping.",
                            )
                            continue
                    else:
                        logger.warning(
                            f"View '{view_str}' for item {item_repr} has no build_file "
                            f"or get_content method. Skipping.",
                        )
                        continue

                    if content is None:
                        logger.warning(
                            f"Content for view '{view_str}' with item {item_repr} "
                            f"was None. Skipping.",
                        )
                        continue

                    output_path = (
                        output_path_override
                        if output_path_override
                        else self.get_build_path(current_url)
                    )
                    logger.debug(f"Building {output_path} for item {item_repr}")
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with output_path.open("wb") as f:
                        f.write(content)

                except Exception as e:
                    err_url_msg = (
                        current_url if "current_url" in locals() and current_url else "N/A"
                    )
                    logger.error(
                        f"Error building page for view '{view_str}' with item "
                        f"{item_repr} (URL/Path: {err_url_msg}): {e}",
                        exc_info=True,
                    )
                    continue
