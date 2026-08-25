from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest
from django.conf import settings
from django.http import Http404
from django.test import RequestFactory, override_settings
from django.urls import resolve

from bakery import feeds, static_urls
from bakery.management.commands import batch_delete_s3_objects, buildserver
from bakery.management.commands import publish as publish_command
from bakery.views import BuildableDetailView, BuildableListView, BuildableMixin


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


def test_publish_boolean_options_default_to_false() -> None:
    parser = publish_command.Command().create_parser("manage.py", "publish")

    options = parser.parse_args([])

    assert options.force is False
    assert options.dry_run is False


def test_batch_delete_honors_chunk_size() -> None:
    s3_client = Mock()

    batch_delete_s3_objects(
        ["one", "two", "three", "four", "five"],
        "bucket",
        chunk_size=2,
        s3_client=s3_client,
    )

    assert s3_client.delete_objects.call_args_list == [
        call(
            Bucket="bucket",
            Delete={"Objects": [{"Key": "one"}, {"Key": "two"}]},
        ),
        call(
            Bucket="bucket",
            Delete={"Objects": [{"Key": "three"}, {"Key": "four"}]},
        ),
        call(Bucket="bucket", Delete={"Objects": [{"Key": "five"}]}),
    ]


def test_static_urls_catch_all_pattern_uses_build_directory() -> None:
    match = resolve("/index.html", urlconf=static_urls)

    assert match.func is static_urls.serve
    assert match.args == ("index.html",)
    assert match.kwargs == {
        "document_root": settings.BUILD_DIR,
        "show_indexes": True,
        "default": "index.html",
    }


def test_static_view_rejects_symlink_outside_document_root(tmp_path: Path) -> None:
    document_root = tmp_path / "public"
    document_root.mkdir()
    private_file = tmp_path / "private.txt"
    private_file.write_text("private")
    (document_root / "link.txt").symlink_to(private_file)

    with pytest.raises(Http404):
        static_urls.serve(
            RequestFactory().get("/link.txt"),
            "link.txt",
            document_root=document_root,
        )


def test_static_view_redirect_stays_on_origin(tmp_path: Path) -> None:
    response = static_urls.serve(
        RequestFactory().get("/../index.html"),
        "../index.html",
        document_root=tmp_path,
    )

    assert response.url == "/index.html"


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


def test_buildable_request_marks_static_builds() -> None:
    request = BuildableMixin().create_request("/example/?preview=true")

    assert request.method == "GET"
    assert request.get_full_path() == "/example/?preview=true"
    assert request.headers["X-Bakery"] == "true"
    assert request.META["HTTP_X_BAKERY"] == "true"


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
