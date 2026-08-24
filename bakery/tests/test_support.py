from unittest.mock import patch

from django.conf import settings
from django.urls import resolve

from bakery import feeds, static_urls
from bakery.management.commands import buildserver


def test_buildserver_uses_static_urlconf() -> None:
    observed_urlconf: list[object] = []

    def delegated_handle(command: object, *args: object, **kwargs: object) -> None:
        observed_urlconf.append(settings.ROOT_URLCONF)

    command = buildserver.Command()
    with patch(
        "bakery.management.commands.buildserver.runserver.Command.handle",
        side_effect=delegated_handle,
    ) as handle:
        result = command.handle("127.0.0.1:8000", verbosity=0)

    assert result is None
    assert observed_urlconf == ["bakery.static_urls"]
    handle.assert_called_once_with(command, "127.0.0.1:8000", verbosity=0)


def test_static_urls_catch_all_pattern_uses_build_directory() -> None:
    match = resolve("/index.html", urlconf=static_urls)

    assert match.func is static_urls.serve
    assert match.args == ("index.html",)
    assert match.kwargs == {
        "document_root": settings.BUILD_DIR,
        "show_indexes": True,
        "default": "index.html",
    }


def test_buildable_feed_supports_callable_attributes() -> None:
    class CallableAttribute:
        def __call__(self, obj: object) -> object:
            return obj

    feed = feeds.BuildableFeed()
    feed.dynamic_value = CallableAttribute()

    subject = object()

    assert feed._get_bakery_dynamic_attr("dynamic_value", subject) is subject
