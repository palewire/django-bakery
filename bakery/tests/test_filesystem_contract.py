"""Behavioral contract for the filesystem adapter used by bakery builds."""

import gzip
import io
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Protocol
from unittest.mock import patch

import pytest
from django.apps import apps
from django.core.management import call_command

from bakery.filesystem import RootedFilesystem, _Filesystem
from bakery.management.commands.build import Command
from bakery.views import BuildableTemplateView
from bakery.views.base import BuildableMixin


class FilesystemContractView(BuildableTemplateView):
    build_path = "pages/index.html"
    template_name = "templateview.html"


class WritableFilesystem(Protocol):
    """The operations buildable views use from an output backend."""

    def exists(self, path: str) -> bool: ...

    def makedirs(self, path: str) -> None: ...

    def open(self, path: str, mode: str) -> BinaryIO: ...

    def removetree(self, path: str) -> None: ...


@contextmanager
def configured_filesystem(filesystem: WritableFilesystem, name: str) -> Iterator[None]:
    """Connect a filesystem to the command and buildable views for one build."""
    app = apps.get_app_config("bakery")
    with (
        patch.object(app, "filesystem", filesystem),
        patch.object(app, "filesystem_name", name),
        patch.object(BuildableMixin, "fs", filesystem),
        patch.object(BuildableMixin, "fs_name", name),
    ):
        yield


def filesystem_snapshot(filesystem: RootedFilesystem) -> dict[str, bytes]:
    """Return backend-relative output paths and their exact bytes."""
    return {
        file_path: filesystem.read_bytes(file_path) for file_path in filesystem.files()
    }


def build_snapshot(
    settings,
    filesystem: RootedFilesystem,
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
    filesystem = RootedFilesystem.from_url(local_name)
    output = build_snapshot(settings, filesystem, local_name, gzip_enabled=True)

    assert_expected_snapshot(output)
    assert {
        path.relative_to(local_root).as_posix()
        for path in local_root.rglob("*")
        if path.is_file()
    } == set(output)
    assert not (tmp_path / "site").exists()


def test_rooted_memory_backend_keeps_output_within_selected_root(settings) -> None:
    filesystem = RootedFilesystem.from_url("mem://selected-root")
    output = build_snapshot(
        settings, filesystem, "mem://selected-root", gzip_enabled=True
    )

    assert_expected_snapshot(output)
    assert all(
        filesystem.filesystem.exists(f"/selected-root/{file_path}")
        for file_path in output
    )
    assert not filesystem.filesystem.exists("/site/pages/index.html")


def test_local_and_memory_backends_use_equivalent_media_paths(
    settings, tmp_path: Path
) -> None:
    local_root = tmp_path / "local-root"
    local_root.mkdir()
    local_name = f"osfs://{local_root}"
    local_filesystem = RootedFilesystem.from_url(local_name)
    memory_filesystem = RootedFilesystem.from_url("mem://memory-root")
    local_output = build_snapshot(
        settings, local_filesystem, local_name, gzip_enabled=True
    )
    memory_output = build_snapshot(
        settings, memory_filesystem, "mem://memory-root", gzip_enabled=True
    )

    assert local_output == memory_output


def test_pooled_and_non_pooled_gzip_builds_produce_identical_output(settings) -> None:
    non_pooled = RootedFilesystem.from_url("mem://non-pooled")
    pooled = RootedFilesystem.from_url("mem://pooled")
    non_pooled_output = build_snapshot(
        settings, non_pooled, "mem://non-pooled", gzip_enabled=True
    )
    pooled_output = build_snapshot(
        settings, pooled, "mem://pooled", gzip_enabled=True, pooling=True
    )

    assert_expected_snapshot(non_pooled_output)
    assert_expected_snapshot(pooled_output)
    assert pooled_output == non_pooled_output


def test_unbuild_removes_a_local_build_directory(settings, tmp_path: Path) -> None:
    build_directory = tmp_path / "build"
    filesystem = RootedFilesystem.from_url("osfs:///")
    settings.BUILD_DIR = str(build_directory)
    settings.BAKERY_FILESYSTEM = "osfs:///"
    settings.BAKERY_VIEWS = (
        "bakery.tests.test_filesystem_contract.FilesystemContractView",
    )

    with configured_filesystem(filesystem, "osfs:///"):
        call_command("build")
        assert (build_directory / "pages" / "index.html").exists()
        call_command("unbuild")

    assert not build_directory.exists()


def test_absolute_and_relative_posix_build_paths_share_the_build_prefix(
    settings,
) -> None:
    filesystem = RootedFilesystem.from_url("mem://absolute-and-relative")
    settings.BUILD_DIR = "site"

    with configured_filesystem(filesystem, "mem://absolute-and-relative"):
        BuildableTemplateView(
            build_path="/absolute/index.html",
            template_name="templateview.html",
        ).build()
        BuildableTemplateView(
            build_path="relative/index.html",
            template_name="templateview.html",
        ).build()
        output = filesystem_snapshot(filesystem)

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


class HistoricalPrepDirectoryView(BuildableTemplateView):
    """A view that uses the long-standing relative prep_directory contract."""

    build_path = "historical/nested/index.html"
    template_name = "templateview.html"
    prep_paths: list[str]

    def prep_directory(self, target_dir: str) -> None:
        self.prep_paths.append(target_dir)
        super().prep_directory(target_dir)


def test_prep_directory_accepts_build_relative_paths_with_a_rooted_backend(
    settings,
) -> None:
    filesystem = RootedFilesystem.from_url("mem://historical-prep")
    settings.BUILD_DIR = "site"
    view = HistoricalPrepDirectoryView()
    view.prep_paths = []

    with configured_filesystem(filesystem, "mem://historical-prep"):
        view.build()
        output = filesystem_snapshot(filesystem)

    assert view.prep_paths == ["historical/nested/index.html"]
    assert set(output) == {"site/historical/nested/index.html"}
    assert filesystem.filesystem.exists("/historical-prep/site/historical/nested")
    assert not filesystem.filesystem.exists("/site/historical/nested")


def test_windows_style_build_paths_are_normalized_without_platform_assumptions(
    settings,
) -> None:
    filesystem = RootedFilesystem.from_url("mem://windows-style")
    settings.BUILD_DIR = "site"

    with configured_filesystem(filesystem, "mem://windows-style"):
        BuildableTemplateView(
            build_path=r"windows\nested\index.html",
            template_name="templateview.html",
        ).build()
        output = filesystem_snapshot(filesystem)

    assert set(output) == {"site/windows/nested/index.html"}


@pytest.mark.parametrize("build_dir", ["", "."])
def test_empty_build_directory_stays_within_selected_backend_root(
    settings, build_dir: str
) -> None:
    filesystem = RootedFilesystem.from_url("mem://empty-build-dir")
    settings.BUILD_DIR = build_dir

    with configured_filesystem(filesystem, "mem://empty-build-dir"):
        BuildableTemplateView(
            build_path="index.html",
            template_name="templateview.html",
        ).build()
        output = filesystem_snapshot(filesystem)

    assert set(output) == {"index.html"}
    assert filesystem.filesystem.exists("/empty-build-dir/index.html")
    assert not filesystem.filesystem.exists("/index.html")


@pytest.mark.parametrize("build_dir", ["", "."])
@pytest.mark.parametrize("backend", ["local", "memory"])
def test_build_and_unbuild_clear_a_rooted_empty_build_directory(
    settings, tmp_path: Path, build_dir: str, backend: str
) -> None:
    if backend == "local":
        root = tmp_path / f"{build_dir or 'empty'}-root"
        root.mkdir()
        filesystem_name = f"osfs://{root}"
    else:
        root = Path(f"/{build_dir or 'empty'}-root")
        filesystem_name = f"mem://{root.name}"
    filesystem = RootedFilesystem.from_url(filesystem_name)
    settings.BUILD_DIR = build_dir
    settings.BAKERY_FILESYSTEM = filesystem_name
    settings.BAKERY_VIEWS = (
        "bakery.tests.test_filesystem_contract.FilesystemContractView",
    )

    with configured_filesystem(filesystem, filesystem_name):
        call_command("build", skip_static=True, skip_media=True)
        with filesystem.open("stale.txt", "wb") as stale_file:
            stale_file.write(b"stale")
        call_command("build", skip_static=True, skip_media=True)
        output = filesystem_snapshot(filesystem)
        call_command("unbuild")

    assert "stale.txt" not in output
    assert set(output) == {"pages/index.html"}
    assert not filesystem.filesystem.exists(str(root))


@pytest.mark.parametrize("build_dir", ["site", "", "."])
def test_build_paths_cannot_escape_the_configured_build_prefix(
    settings, build_dir: str
) -> None:
    filesystem = RootedFilesystem.from_url("mem://escape")
    settings.BUILD_DIR = build_dir

    with configured_filesystem(filesystem, "mem://escape"):
        with pytest.raises(ValueError, match="BUILD_DIR"):
            BuildableTemplateView(
                build_path="../outside.html",
                template_name="templateview.html",
            ).build()
        output = filesystem_snapshot(filesystem)

    assert set(output) == set()


class ChunkedSource(io.BytesIO):
    """A source stream that rejects reads without a bounded size."""

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            raise AssertionError("copy_local_file must use bounded reads")
        return super().read(size)


def test_copy_local_file_streams_source_in_chunks(monkeypatch) -> None:
    filesystem = RootedFilesystem.from_url("mem://streaming-copy")
    source = ChunkedSource(b"large enough to require more than one chunk")
    expected = source.getvalue()
    command = Command()
    command.fs = filesystem

    monkeypatch.setattr(Path, "open", lambda *_args, **_kwargs: source)

    command.copy_local_file("source.bin", "assets/source.bin")

    assert filesystem.read_bytes("assets/source.bin") == expected


class RecordingFilesystem:
    """A minimal fsspec-like backend for URL-root parsing tests."""

    def exists(self, _path: str) -> bool:
        return False

    def makedirs(self, _path: str, exist_ok: bool) -> None:
        assert exist_ok

    def open(self, _path: str, _mode: str) -> BinaryIO:
        raise AssertionError("This test only resolves paths")

    def rm(self, _path: str, recursive: bool) -> None:
        assert recursive

    def copy(self, _source: str, _target: str) -> None:
        raise AssertionError("This test only resolves paths")

    def find(self, _path: str) -> list[str]:
        return []


def test_windows_drive_root_from_url_is_unrooted(monkeypatch) -> None:
    backend: _Filesystem = RecordingFilesystem()
    monkeypatch.setattr("bakery.filesystem.url_to_fs", lambda _url: (backend, "C:/"))

    filesystem = RootedFilesystem.from_url("osfs:///")

    assert filesystem.root == ""
    assert filesystem._resolve("C:/site/index.html") == "C:/site/index.html"


@pytest.mark.parametrize(
    ("url", "expected_root"),
    [
        ("osfs:///", ""),
        ("osfs:///tmp/bakery-output", "/tmp/bakery-output"),
        ("mem://", ""),
        ("mem://bakery-output", "/bakery-output"),
    ],
)
def test_documented_filesystem_urls_use_expected_roots(
    url: str, expected_root: str
) -> None:
    filesystem = RootedFilesystem.from_url(url)

    assert filesystem.root == expected_root
