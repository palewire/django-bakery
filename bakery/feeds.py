import logging

from django.contrib.syndication.views import Feed

# Assuming BuildableMixin is in bakery.views.base
from bakery.views.base import BuildableMixin

logger = logging.getLogger(__name__)


class BuildableFeed(Feed, BuildableMixin):
    """
    Extends the base Django Feed class to be buildable.
    """

    # build_path is the path relative to BUILD_DIR where the feed will be saved.
    # It can be a string or a method that returns a string.
    # If it's a method, it can optionally take an 'obj' argument if the
    # feed is built per-object.
    build_path = "feed.xml"  # Default for single-instance feeds

    # feed_url is used to set the <link> in the feed.
    # It can be a string or a method. If a method, it can take an 'obj'.
    # If not provided, build_path is often used as a fallback for the request path.

    def get_content(self, *args, **kwargs) -> bytes:
        """
        Renders the feed content using Django's syndication framework.
        Ensures self.request is set and content is returned as bytes.
        """
        # Ensure self.request is set before calling the Feed's __call__ method
        if not hasattr(self, "request") or self.request is None:
            # Determine a sensible request path
            req_path = "/"
            obj = kwargs.get("obj", args[0] if args else None)  # Try to get obj if passed

            # Try to get feed_url first, then build_path
            # _get_bakery_dynamic_attr handles if these are methods or attributes
            try:
                # Pass obj if the feed_url method might expect it
                req_path = self._get_bakery_dynamic_attr("feed_url", obj)
                if not req_path:  # Fallback if feed_url is None or empty
                    req_path = self._get_bakery_dynamic_attr("build_path", obj, default="/")
            except Exception as e:
                logger.warning(
                    f"Could not determine request path for "
                    f"{self.get_class_name()}: {e}. Defaulting to '/'.",
                )
                req_path = self._get_bakery_dynamic_attr("build_path", obj, default="/")

            self.request = self.create_request(req_path or "/")

        feed_content = self(self.request, *args, **kwargs).content
        if isinstance(feed_content, str):
            return feed_content.encode("utf-8")
        return feed_content

    @property
    def build_method(self):
        """
        Specifies that building this feed involves iterating through its queryset
        (even if the queryset is just [None] for a single feed).
        """
        return self.build_queryset

    def _get_bakery_dynamic_attr(self, attname, obj, args=None, default=None):
        """
        Allows subclasses to provide an attribute (say, 'foo') in three
        different ways: As a fixed class-level property or as a method
        foo(self) or foo(self, obj). The second argument argument 'obj' is
        the "subject" of the current Feed invocation. See the Django Feed
        documentation for details.

        This method was shamelessly stolen from the Feed class and extended
        with the ability to pass additional arguments to subclass methods.
        """
        try:
            attr = getattr(self, attname)
        except AttributeError:
            return default

        # Prepare arguments for callable attributes
        call_args = list(args) if args else []

        if callable(attr):
            # Check co_argcount rather than try/excepting the function and
            # catching the TypeError, because something inside the function
            # may raise the TypeError. This technique is more accurate.
            try:
                code = attr.__code__
            except AttributeError:  # For methods bound to instances or other callables
                code = attr.__call__.__code__

            # co_argcount includes 'self'. If obj is relevant, it's an additional arg.
            # If the callable expects obj and obj is provided
            if obj is not None and code.co_argcount == (
                1 + len(call_args) + 1
            ):  # self + call_args + obj
                call_args.append(obj)
            # If the callable does not expect obj, or obj is None, but matches arg count
            elif code.co_argcount == (1 + len(call_args)):  # self + call_args
                pass  # call_args is already set
            else:
                # This case means the callable's signature doesn't match expected patterns
                # for obj handling. It might be a simple method not expecting obj,
                # or a mismatch. For safety, we don't add obj if not explicitly matched.
                # Or, if it's a simple attribute, it's returned directly below.
                # If it's a method that *always* takes obj, this logic is fine.
                # If it's a method that *sometimes* takes obj, the caller needs to be aware.
                # The original logic was: if code.co_argcount == 2 + len(args): args.append(obj)
                # This assumed 'args' was the *additional* args beyond self and obj.
                # Let's refine:
                pass  # Current call_args is what we have

            try:
                return attr(*call_args)
            except TypeError as e:
                # This can happen if the signature was misjudged.
                # Example: method expects obj, but obj was None and not added.
                logger.warning(
                    f"TypeError calling dynamic attribute {attname} on "
                    f"{self.get_class_name()} with args {call_args}: {e}",
                )
                # Fallback to returning the attribute itself if it's not callable with these args,
                # or re-raise / return default.
                # For now, let's try calling without obj if obj was the last
                # added and might be the issue.
                if obj is not None and call_args and call_args[-1] is obj:
                    try:
                        return attr(*call_args[:-1])
                    except TypeError:
                        pass  # Still fails, proceed to return attr or default
                # If it was a simple attribute, it's returned below.
                # If it was a method that failed, this might be an issue.
                # The original Django Feed._get_dynamic_attr is simpler and might be safer.
                # However, this one tries to support extra 'args'.
                # For now, if callable fails, we fall through to returning
                # attr if not callable, or default.
                # This part is complex and might need more specific use-case testing.
                # Let's stick closer to the original intent for obj:
                if (
                    obj is not None and hasattr(code, "co_argcount") and code.co_argcount == 2
                ):  # self, obj
                    return attr(obj)
                elif hasattr(code, "co_argcount") and code.co_argcount == 1:  # self
                    return attr()
                # If it has other args, this custom logic is more involved.
                # For simplicity and robustness, often better to have distinct methods.

        return attr  # Return the attribute value directly if not callable or
        # if callable logic didn't apply

    def get_queryset(self):
        """
        Defines the list of items to build. For a single feed file (not
        per-object), this can return a list with a single None item.
        """
        return [None]  # Default for a feed that builds only one file

    def build_queryset(self):
        """
        Builds the feed for each item in the queryset.
        """
        for obj in self.get_queryset():
            # Determine the relative build path for this feed instance (or object)
            # self.build_path can be an attribute or a method (that might take obj)
            relative_build_path = self._get_bakery_dynamic_attr("build_path", obj, default=None)
            if relative_build_path is None:
                logger.error(
                    f"Could not determine build_path for feed "
                    f"{self.get_class_name()} with obj {obj}. Skipping.",
                )
                continue

            # Determine the URL for the request (often the feed's public URL)
            # self.feed_url is a standard Django Feed attribute.
            # It can be an attribute or a method (that might take obj).
            request_url = self._get_bakery_dynamic_attr("feed_url", obj, default=None)
            if request_url is None:
                # Fallback to using the build_path as the request URL if feed_url isn't defined
                request_url = f"/{relative_build_path.lstrip('/')}"
                logger.debug(
                    f"feed_url not found for {self.get_class_name()}, "
                    f"using request_url: {request_url} based on build_path",
                )

            logger.debug(
                f"Building feed {self.get_class_name()} to relative path: {relative_build_path}",
            )

            # Create a request object. get_content will use this.
            # The create_request method is from BuildableMixin.
            self.request = self.create_request(request_url)

            # Get the feed content (which will call self.get_content defined above)
            # The get_content method in this class ensures self.request is set
            # and calls the Feed's rendering logic.
            # We pass 'obj' here if get_content or the underlying Feed methods need it.
            content_bytes = self.get_content(obj=obj)  # Pass obj to get_content

            # Build the file using the relative path.
            # build_file is from BuildableMixin and handles directory creation and gzipping.
            self.build_file(relative_build_path, content_bytes)
