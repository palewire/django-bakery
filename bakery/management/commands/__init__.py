import logging
from collections.abc import Iterable, Mapping
from typing import Protocol, TypeAlias, cast

import boto3
from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

S3Object: TypeAlias = Mapping[str, object]
S3Page: TypeAlias = Mapping[str, list[S3Object]]
S3ObjectDict: TypeAlias = dict[str, S3Object]


class S3Paginator(Protocol):
    def paginate(self, **kwargs: str) -> Iterable[S3Page]: ...


class S3Client(Protocol):
    def get_paginator(self, operation_name: str) -> S3Paginator: ...

    def delete_objects(
        self,
        *,
        Bucket: str,  # noqa: N803
        Delete: Mapping[str, list[dict[str, str]]],  # noqa: N803
    ) -> object: ...


class S3Bucket(Protocol): ...


class S3UploadObject(Protocol):
    def upload_file(
        self,
        filename: str,
        *,
        ExtraArgs: Mapping[str, str],  # noqa: N803
    ) -> object: ...


class S3Resource(Protocol):
    def Bucket(self, name: str) -> S3Bucket: ...  # noqa: N802

    def Object(self, bucket_name: str, key: str) -> S3UploadObject: ...  # noqa: N802


def get_s3_client() -> tuple[S3Client, S3Resource]:
    """
    A DRY place to make sure AWS credentials in settings override
    environment based credentials.  Boto3 will fall back to:
    http://boto3.readthedocs.io/en/latest/guide/configuration.html
    """
    session_kwargs = {}
    if hasattr(settings, "AWS_ACCESS_KEY_ID"):
        session_kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID

    if hasattr(settings, "AWS_SECRET_ACCESS_KEY"):
        session_kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
    boto3.setup_default_session(**session_kwargs)

    s3_kwargs = {}
    if hasattr(settings, "AWS_S3_ENDPOINT"):
        s3_kwargs["endpoint_url"] = settings.AWS_S3_ENDPOINT
    elif hasattr(settings, "AWS_S3_HOST"):
        if hasattr(settings, "AWS_S3_USE_SSL") and settings.AWS_S3_USE_SSL is False:
            protocol = "http://"
        else:
            protocol = "https://"
        s3_kwargs["endpoint_url"] = f"{protocol}{settings.AWS_S3_HOST}"
    if hasattr(settings, "AWS_REGION"):
        s3_kwargs["region_name"] = settings.AWS_REGION
    s3_client = boto3.client("s3", **s3_kwargs)
    s3_resource = boto3.resource("s3", **s3_kwargs)
    return cast("S3Client", s3_client), cast("S3Resource", s3_resource)


def get_bucket_page(page: S3Page) -> S3ObjectDict:
    """
    Returns all the keys in a s3 bucket paginator page.
    """
    key_list = page.get("Contents", [])
    logger.debug("Retrieving page with %s keys", len(key_list))
    return {cast("str", key.get("Key")): key for key in key_list}


def get_all_objects_in_bucket(
    aws_bucket_name: str, s3_client: S3Client | None = None, max_keys: int = 1000
) -> S3ObjectDict:
    """
    Little utility method that handles pagination and returns
    all objects in given bucket.
    """
    logger.debug("Retrieving bucket object list")

    if not s3_client:
        s3_client, _s3_resource = get_s3_client()

    obj_dict = {}
    paginator = s3_client.get_paginator("list_objects")
    page_iterator = paginator.paginate(Bucket=aws_bucket_name)
    for page in page_iterator:
        key_list = page.get("Contents", [])
        logger.debug("Loading page with %s keys", len(key_list))
        for obj in key_list:
            obj_dict[cast("str", obj.get("Key"))] = obj
    return obj_dict


def batch_delete_s3_objects(
    keys: Iterable[str],
    aws_bucket_name: str,
    chunk_size: int = 100,
    s3_client: S3Client | None = None,
) -> None:
    """
    Utility method that batch deletes objects in given bucket.
    """
    if s3_client is None:
        s3_client, _s3_resource = get_s3_client()

    key_list = list(keys)
    key_chunks = []
    for i in range(0, len(key_list), chunk_size):
        chunk = []
        for key in key_list[i : i + chunk_size]:
            chunk.append({"Key": key})
        key_chunks.append(chunk)
    for chunk in key_chunks:
        s3_client.delete_objects(Bucket=aws_bucket_name, Delete={"Objects": chunk})


class BasePublishCommand(BaseCommand):
    """
    Base command that exposes these utility methods to the Management
    Commands that need them.
    """

    def get_s3_client(self) -> tuple[S3Client, S3Resource]:
        return get_s3_client()

    def get_all_objects_in_bucket(
        self,
        aws_bucket_name: str,
        s3_client: S3Client | None = None,
        max_keys: int = 1000,
    ) -> S3ObjectDict:
        return get_all_objects_in_bucket(aws_bucket_name, s3_client, max_keys)

    def batch_delete_s3_objects(
        self,
        keys: Iterable[str],
        aws_bucket_name: str,
        chunk_size: int = 100,
        s3_client: S3Client | None = None,
    ) -> None:
        return batch_delete_s3_objects(keys, aws_bucket_name, chunk_size, s3_client)
