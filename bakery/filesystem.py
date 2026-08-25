"""Rooted filesystem support for bakery output."""

import mimetypes
import posixpath
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from os import PathLike
from typing import BinaryIO, Protocol, cast
from urllib.parse import urlsplit

from botocore.exceptions import BotoCoreError
from fsspec.core import url_to_fs


class _Filesystem(Protocol):
    def exists(self, path: str) -> bool: ...

    def info(self, path: str) -> object: ...

    def makedirs(self, path: str, exist_ok: bool) -> None: ...

    def open(self, path: str, mode: str, **kwargs: object) -> BinaryIO: ...

    def rm(self, path: str | list[str], recursive: bool) -> list[str] | None: ...

    def copy(self, source: str, target: str) -> None: ...

    def find(self, path: str) -> list[str]: ...


class _S3Filesystem(_Filesystem, Protocol):
    """The configured s3fs operations used for bucket-safe cleanup."""

    def call_s3(
        self, method: str, *args: object, **kwargs: object
    ) -> Mapping[str, object]: ...


@dataclass(frozen=True)
class ObjectMetadata:
    """HTTP metadata that can be applied to a written output object."""

    content_type: str
    content_encoding: str | None = None


def object_metadata(path: str | PathLike[str]) -> ObjectMetadata:
    """Infer HTTP metadata for an output path."""
    content_type, _ = mimetypes.guess_type(str(path))
    return ObjectMetadata(content_type=content_type or "application/octet-stream")


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

    def __init__(
        self,
        filesystem: _Filesystem,
        root: str = "",
        *,
        s3_bucket: str | None = None,
    ) -> None:
        self.filesystem = filesystem
        self.root = self._normalize_root(root)
        self.s3_bucket = s3_bucket

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
            return cls(cast("_Filesystem", filesystem), root, s3_bucket=parsed.netloc)
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
        if self.s3_bucket:
            return
        self.filesystem.makedirs(self._resolve(path), exist_ok=True)

    def validate(self) -> None:
        """Check a configured S3 bucket immediately before command I/O."""
        if not self.s3_bucket:
            return
        try:
            self.filesystem.info(self.s3_bucket)
        except FileNotFoundError as exc:
            raise ValueError(
                f"Configured S3 bucket {self.s3_bucket!r} must already exist."
            ) from exc
        except (OSError, BotoCoreError) as exc:
            raise ValueError(
                f"Configured S3 bucket {self.s3_bucket!r} is not accessible."
            ) from exc

    def open(
        self,
        path: str | PathLike[str],
        mode: str,
        *,
        metadata: ObjectMetadata | None = None,
    ) -> BinaryIO:
        if self.s3_bucket and metadata:
            kwargs: dict[str, str] = {"ContentType": metadata.content_type}
            if metadata.content_encoding:
                kwargs["ContentEncoding"] = metadata.content_encoding
            return self.filesystem.open(self._resolve(path), mode, **kwargs)
        return self.filesystem.open(self._resolve(path), mode)

    def removetree(self, path: str | PathLike[str]) -> None:
        resolved = self._resolve(path)
        if not self.s3_bucket:
            self.filesystem.rm(resolved, recursive=True)
            return

        root_key = self._s3_key(resolved)
        object_keys = [
            key
            for candidate in self.filesystem.find(resolved)
            if (key := self._s3_key(candidate)) is not None
            and self._is_s3_key_within(key, root_key)
        ]
        s3_filesystem = cast("_S3Filesystem", self.filesystem)
        for start in range(0, len(object_keys), 1000):
            keys = object_keys[start : start + 1000]
            response = s3_filesystem.call_s3(
                "delete_objects",
                Bucket=self.s3_bucket,
                Delete={
                    "Objects": [{"Key": key} for key in keys],
                    "Quiet": False,
                },
            )
            self._raise_s3_delete_errors(response, resolved)

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

    def _s3_key(self, path: str) -> str | None:
        """Return a literal S3 key, never a bucket-like fsspec path."""
        if not self.s3_bucket or path == self.s3_bucket:
            return None
        bucket_prefix = f"{self.s3_bucket}/"
        if not path.startswith(bucket_prefix):
            return None
        key = path.removeprefix(bucket_prefix)
        return key or None

    @staticmethod
    def _is_s3_key_within(key: str, root_key: str | None) -> bool:
        """Return whether an object key belongs to the selected cleanup root."""
        return root_key is None or key == root_key or key.startswith(f"{root_key}/")

    @staticmethod
    def _raise_s3_delete_errors(response: Mapping[str, object], path: str) -> None:
        """Raise any per-object errors reported by a DeleteObjects response."""
        errors = response.get("Errors", [])
        if not isinstance(errors, list) or not errors:
            return
        failed_keys = [
            str(error.get("Key", "<unknown>"))
            for error in errors
            if isinstance(error, Mapping)
        ]
        detail = ", ".join(failed_keys) or "<unknown>"
        raise OSError(f"Unable to delete S3 objects below {path!r}: {detail}.")

    @staticmethod
    def _normalize_root(root: str) -> str:
        """Keep filesystem markers, including Windows drive roots, unrooted."""
        if root in {"", "/"} or re.fullmatch(r"[A-Za-z]:/", root):
            return ""
        return root.rstrip("/")
