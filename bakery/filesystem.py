"""Rooted filesystem support for bakery output."""

import posixpath
import re
from collections.abc import Iterator
from os import PathLike
from typing import BinaryIO, Protocol, cast
from urllib.parse import urlsplit

from fsspec.core import url_to_fs


class _Filesystem(Protocol):
    def exists(self, path: str) -> bool: ...

    def makedirs(self, path: str, exist_ok: bool) -> None: ...

    def open(self, path: str, mode: str) -> BinaryIO: ...

    def rm(self, path: str, recursive: bool) -> None: ...

    def copy(self, source: str, target: str) -> None: ...

    def find(self, path: str) -> list[str]: ...


def normalize_path(path: str | PathLike[str]) -> str:
    """Return a portable POSIX path without changing its absolute form."""
    return posixpath.normpath(str(path).replace("\\", "/"))


def join_path(*paths: str | PathLike[str]) -> str:
    """Join filesystem paths with POSIX separators."""
    return posixpath.join(*(str(path).replace("\\", "/") for path in paths))


def is_root_path(path: str | PathLike[str]) -> bool:
    """Return whether a path identifies a filesystem root."""
    normalized = normalize_path(path)
    return normalized in {".", "/", "//"} or bool(
        re.fullmatch(r"[A-Za-z]:/?", normalized)
    )


class RootedFilesystem:
    """Expose paths relative to a configured fsspec filesystem URL."""

    def __init__(self, filesystem: _Filesystem, root: str = "") -> None:
        self.filesystem = filesystem
        self.root = self._normalize_root(root)

    @classmethod
    def from_url(cls, url: str) -> "RootedFilesystem":
        """Create an adapter for a documented Bakery filesystem URL."""
        if url.startswith("osfs://"):
            url = f"file://{url.removeprefix('osfs://')}"
        elif url.startswith("mem://"):
            url = f"memory://{url.removeprefix('mem://')}"
        elif url.startswith("s3://"):
            parsed = urlsplit(url)
            prefix_parts = parsed.path.replace("\\", "/").split("/")
            if (
                not parsed.netloc
                or parsed.query
                or parsed.fragment
                or ".." in prefix_parts
            ):
                raise ValueError(
                    "BAKERY_FILESYSTEM must use s3://bucket[/prefix] without "
                    "query, fragment, or traversal components."
                )
            root = join_path(
                parsed.netloc,
                *(part for part in prefix_parts if part not in {"", "."}),
            )
            filesystem, _ = url_to_fs(f"s3://{parsed.netloc}")
            return cls(cast("_Filesystem", filesystem), root)
        else:
            raise ValueError(
                "BAKERY_FILESYSTEM must use a supported osfs:///, mem://, or "
                "s3://bucket[/prefix] URL."
            )
        filesystem, root = url_to_fs(url)
        return cls(cast("_Filesystem", filesystem), cast("str", root))

    def exists(self, path: str | PathLike[str]) -> bool:
        return self.filesystem.exists(self._resolve(path))

    def makedirs(self, path: str | PathLike[str]) -> None:
        self.filesystem.makedirs(self._resolve(path), exist_ok=True)

    def open(self, path: str | PathLike[str], mode: str) -> BinaryIO:
        return self.filesystem.open(self._resolve(path), mode)

    def removetree(self, path: str | PathLike[str]) -> None:
        self.filesystem.rm(self._resolve(path), recursive=True)

    def copy(self, source: str | PathLike[str], target: str | PathLike[str]) -> None:
        self.filesystem.copy(self._resolve(source), self._resolve(target))

    def read_bytes(self, path: str | PathLike[str]) -> bytes:
        with self.open(path, "rb") as source:
            return source.read()

    def files(self) -> Iterator[str]:
        """Yield backend-relative file names below the configured root."""
        for path in self.filesystem.find(self.root or "/"):
            yield self._relative(path)

    def _resolve(self, path: str | PathLike[str]) -> str:
        portable_path = str(path).replace("\\", "/")
        normalized = normalize_path(portable_path)
        if not self.root:
            return normalized

        if re.match(r"^/*[A-Za-z]:", portable_path):
            raise ValueError(
                "Path is drive-qualified and cannot use a rooted filesystem."
            )
        if ".." in portable_path.split("/"):
            raise ValueError("Path escapes the configured filesystem root.")
        relative = normalized.lstrip("/")
        return normalize_path(join_path(self.root, relative))

    def _relative(self, path: str) -> str:
        if not self.root:
            return path.lstrip("/")
        return path.removeprefix(f"{self.root}/").lstrip("/")

    @staticmethod
    def _normalize_root(root: str) -> str:
        """Keep filesystem markers, including Windows drive roots, unrooted."""
        if root in {"", "/"} or re.fullmatch(r"[A-Za-z]:/", root):
            return ""
        return root.rstrip("/")
