from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import override_settings
from django.urls import resolve

from bakery import feeds, static_urls
from bakery.management.commands import buildserver
from bakery.views import BuildableDetailView, BuildableListView


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


def test_detail_view_supports_dynamic_absolute_url() -> None:
    class DynamicObject:
        def __getattr__(self, name: str) -> object:
            if name == "get_absolute_url":
                return lambda: "/dynamic/"
            raise AttributeError(name)

    assert BuildableDetailView().get_url(DynamicObject()) == "/dynamic/"


@override_settings(BUILD_DIR=Path("/tmp/build"))
def test_list_view_supports_path_build_directory() -> None:
    view = BuildableListView(build_path="index.html")

    with (
        patch.object(view, "create_request", return_value=object()),
        patch.object(view, "prep_directory"),
        patch.object(view, "get_content", return_value=b"content"),
        patch.object(view, "build_file") as build_file,
    ):
        view.build_queryset()

    build_file.assert_called_once_with("/tmp/build/index.html", b"content")
