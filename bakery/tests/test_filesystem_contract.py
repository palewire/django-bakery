"""Behavioral contract for the filesystem adapter used by bakery builds."""

import gzip
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO
from unittest.mock import patch

import fs
import pytest
from django.apps import apps
from django.core.management import call_command

from bakery.views import BuildableTemplateView
from bakery.views.base import BuildableMixin


class FilesystemContractView(BuildableTemplateView):
    build_path = "pages/index.html"
    template_name = "templateview.html"


@contextmanager
def configured_filesystem(filesystem: fs.base.FS, name: str) -> Iterator[None]:
    """Connect a filesystem to the command and buildable views for one build."""
    app = apps.get_app_config("bakery")
    with (
        patch.object(app, "filesystem", filesystem),
        patch.object(app, "filesystem_name", name),
        patch.object(BuildableMixin, "fs", filesystem),
        patch.object(BuildableMixin, "fs_name", name),
    ):
        yield


def filesystem_snapshot(filesystem: fs.base.FS) -> dict[str, bytes]:
    """Return backend-relative output paths and their exact bytes."""
    return {
        file_path.lstrip("/"): filesystem.readbytes(file_path)
        for file_path in filesystem.walk.files()
    }


def build_snapshot(
    settings,
    filesystem: fs.base.FS,
    filesystem_name: str,
    *,
    gzip_enabled: bool = False,
    pooling: bool = False,
) -> dict[str, bytes]:
    settings.BUILD_DIR = "site"
    settings.BAKERY_FILESYSTEM = filesystem_name
    settings.BAKERY_GZIP = gzip_enabled
    settings.BAKERY_VIEWS = (
        "bakery.tests.test_filesystem_contract.FilesystemContractView",
    )

    with configured_filesystem(filesystem, filesystem_name):
        call_command("build", pooling=pooling)

    return filesystem_snapshot(filesystem)


def media_output_path(snapshot: dict[str, bytes]) -> str:
    """Find the single copied media file without blessing its current prefix."""
    media_paths = [
        file_path for file_path in snapshot if file_path.endswith("site/media/bar.js")
    ]
    assert len(media_paths) == 1
    return media_paths[0]


def assert_deterministic_gzip(data: bytes, expected: bytes) -> None:
    """Assert gzip content is reproducible and decompresses to the expected bytes."""
    assert data[4:8] == b"\0\0\0\0"
    assert gzip.decompress(data) == expected


def assert_expected_snapshot(snapshot: dict[str, bytes]) -> None:
    """Assert the backend-independent files and bytes from a complete build."""
    assert snapshot
    assert_deterministic_gzip(
        snapshot["site/pages/index.html"], "Hellō tests!\n".encode()
    )
    assert_deterministic_gzip(snapshot["site/robots.txt"], b"Hello robots!\n")
    assert_deterministic_gzip(snapshot["site/static/robots.txt"], b"Hello robots!\n")
    assert_deterministic_gzip(
        snapshot["site/static/test.css"], b"html { display:block; }\n"
    )
    assert snapshot[media_output_path(snapshot)] == b"var test = true;\n"
    assert snapshot["site/static/foo.bar"] == b"Hello tests\n"
    assert snapshot["site/favicon.ico"] == snapshot["site/static/favicon.ico"]


def test_rooted_local_backend_keeps_output_within_selected_root(
    settings, tmp_path: Path
) -> None:
    local_root = tmp_path / "local-root"
    local_root.mkdir()
    local_name = f"osfs://{local_root}"
    filesystem = fs.open_fs(local_name)

    try:
        output = build_snapshot(settings, filesystem, local_name, gzip_enabled=True)
    finally:
        filesystem.close()

    assert_expected_snapshot(output)
    assert {
        path.relative_to(local_root).as_posix()
        for path in local_root.rglob("*")
        if path.is_file()
    } == set(output)
    assert not (tmp_path / "site").exists()


def test_rooted_memory_backend_keeps_output_within_selected_root(settings) -> None:
    parent = fs.open_fs("mem://")
    parent.makedirs("selected-root")
    filesystem = parent.opendir("selected-root")

    try:
        output = build_snapshot(settings, filesystem, "mem://", gzip_enabled=True)
    finally:
        filesystem.close()

    assert_expected_snapshot(output)
    assert all(parent.exists(f"selected-root/{file_path}") for file_path in output)
    assert not parent.exists("site/pages/index.html")
    parent.close()


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Media copying currently includes the BAKERY_FILESYSTEM URL in the "
        "destination path, so rooted local and memory backend paths differ."
    ),
)
def test_local_and_memory_backends_use_equivalent_media_paths(
    settings, tmp_path: Path
) -> None:
    local_root = tmp_path / "local-root"
    local_root.mkdir()
    local_name = f"osfs://{local_root}"
    local_filesystem = fs.open_fs(local_name)
    memory_parent = fs.open_fs("mem://")
    memory_parent.makedirs("memory-root")
    memory_filesystem = memory_parent.opendir("memory-root")

    try:
        local_output = build_snapshot(
            settings, local_filesystem, local_name, gzip_enabled=True
        )
        memory_output = build_snapshot(
            settings, memory_filesystem, "mem://", gzip_enabled=True
        )
    finally:
        local_filesystem.close()
        memory_filesystem.close()
        memory_parent.close()

    assert media_output_path(local_output) == media_output_path(memory_output)


def test_pooled_and_non_pooled_gzip_builds_produce_identical_output(settings) -> None:
    non_pooled = fs.open_fs("mem://")
    pooled = fs.open_fs("mem://")

    try:
        non_pooled_output = build_snapshot(
            settings, non_pooled, "mem://", gzip_enabled=True
        )
        pooled_output = build_snapshot(
            settings, pooled, "mem://", gzip_enabled=True, pooling=True
        )
    finally:
        non_pooled.close()
        pooled.close()

    assert_expected_snapshot(non_pooled_output)
    assert_expected_snapshot(pooled_output)
    assert pooled_output == non_pooled_output


def test_unbuild_removes_a_local_build_directory(settings, tmp_path: Path) -> None:
    build_directory = tmp_path / "build"
    filesystem = fs.open_fs("osfs:///")
    settings.BUILD_DIR = str(build_directory)
    settings.BAKERY_FILESYSTEM = "osfs:///"
    settings.BAKERY_VIEWS = (
        "bakery.tests.test_filesystem_contract.FilesystemContractView",
    )

    try:
        with configured_filesystem(filesystem, "osfs:///"):
            call_command("build")
        assert (build_directory / "pages" / "index.html").exists()

        call_command("unbuild")
    finally:
        filesystem.close()

    assert not build_directory.exists()


def test_absolute_and_relative_posix_build_paths_share_the_build_prefix(
    settings,
) -> None:
    filesystem = fs.open_fs("mem://")
    settings.BUILD_DIR = "site"

    try:
        with configured_filesystem(filesystem, "mem://"):
            BuildableTemplateView(
                build_path="/absolute/index.html",
                template_name="templateview.html",
            ).build()
            BuildableTemplateView(
                build_path="relative/index.html",
                template_name="templateview.html",
            ).build()
    finally:
        output = filesystem_snapshot(filesystem)
        filesystem.close()

    assert set(output) == {
        "site/absolute/index.html",
        "site/relative/index.html",
    }


class FailingFilesystem:
    """A minimal backend that exposes write errors from buildable views."""

    def exists(self, _path: str) -> bool:
        return True

    def makedirs(self, _path: str) -> None:
        raise AssertionError("The failing write should not need a directory")

    def open(self, _path: str, _mode: str) -> BinaryIO:
        raise OSError("backend unavailable")

    def removetree(self, _path: str) -> None:
        raise AssertionError("The failing write should not remove a directory")


def test_backend_write_failures_are_propagated(settings) -> None:
    settings.BUILD_DIR = "site"

    with configured_filesystem(FailingFilesystem(), "failing://"):
        view = BuildableTemplateView(
            build_path="failure.html",
            template_name="templateview.html",
        )
        with pytest.raises(OSError, match="backend unavailable"):
            view.build()


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Windows-style separators are currently passed to the backend as literal "
        "characters instead of normalized POSIX output paths (issue #158)."
    ),
)
def test_windows_style_build_paths_are_normalized_without_platform_assumptions(
    settings,
) -> None:
    filesystem = fs.open_fs("mem://")
    settings.BUILD_DIR = "site"

    try:
        with configured_filesystem(filesystem, "mem://"):
            BuildableTemplateView(
                build_path=r"windows\nested\index.html",
                template_name="templateview.html",
            ).build()
        output = filesystem_snapshot(filesystem)
    finally:
        filesystem.close()

    assert set(output) == {"site/windows/nested/index.html"}


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Relative back-references can currently escape the configured BUILD_DIR "
        "prefix instead of raising ValueError before writing."
    ),
)
def test_build_paths_cannot_escape_the_configured_build_prefix(settings) -> None:
    filesystem = fs.open_fs("mem://")
    settings.BUILD_DIR = "site"

    try:
        with configured_filesystem(filesystem, "mem://"):
            with pytest.raises(ValueError, match="BUILD_DIR"):
                BuildableTemplateView(
                    build_path="../outside.html",
                    template_name="templateview.html",
                ).build()
        output = filesystem_snapshot(filesystem)
    finally:
        filesystem.close()

    assert set(output) == set()
