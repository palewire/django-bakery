import boto3
import logging
from django.conf import settings
from django.core.management.base import BaseCommand
logger = logging.getLogger(__name__)


def get_s3_client():
    """
    A DRY place to make sure AWS credentials in settings override
    environment based credentials.  Boto3 will fall back to:
    http://boto3.readthedocs.io/en/latest/guide/configuration.html
    """
    session_kwargs = {}
    if hasattr(settings, 'AWS_ACCESS_KEY_ID'):
        session_kwargs['aws_access_key_id'] = settings.AWS_ACCESS_KEY_ID

    if hasattr(settings, 'AWS_SECRET_ACCESS_KEY'):
        session_kwargs['aws_secret_access_key'] = settings.AWS_SECRET_ACCESS_KEY
    boto3.setup_default_session(**session_kwargs)

    s3_kwargs = {}
    if hasattr(settings, 'AWS_S3_ENDPOINT'):
        s3_kwargs['endpoint_url'] = settings.AWS_S3_ENDPOINT
    elif hasattr(settings, 'AWS_S3_HOST'):
        if hasattr(settings, 'AWS_S3_USE_SSL') and settings.AWS_S3_USE_SSL is False:
            protocol = "http://"
        else:
            protocol = "https://"
        s3_kwargs['endpoint_url'] = "{}{}".format(
            protocol,
            settings.AWS_S3_HOST
        )
    s3_client = boto3.client('s3', **s3_kwargs)
    s3_resource = boto3.resource('s3', **s3_kwargs)
    return s3_client, s3_resource


def get_all_objects_in_bucket(
        aws_bucket_name,
        s3_client=None,
        max_keys=1000
):
    """
    Little utility method that handles pagination and returns
    all objects in given bucket.
    """
    logger.debug("Retrieving bucket object list")

    if not s3_client:
        s3_client, s3_resource = get_s3_client()

    obj_dict = {}
    continuation_token = ''
    while True:
        kwargs = {'Bucket': aws_bucket_name, 'MaxKeys': max_keys}
        if continuation_token:
            kwargs['ContinuationToken'] = continuation_token

        list_objects_response = s3_client.list_objects_v2(**kwargs)

        key_list = list_objects_response.get('Contents', [])
        logger.debug("Returning {} new keys".format(len(key_list)))

        for obj in key_list:
            obj_dict[obj.get('Key')] = obj

        if not list_objects_response.get('IsTruncated'):
            break

        continuation_token = list_objects_response.get(
            'NextContinuationToken'
        )

    return obj_dict


def batch_delete_s3_objects(
        keys,
        aws_bucket_name,
        chunk_size=100,
        s3_client=None
):
    """
    Utility method that batch deletes objects in given bucket.
    """
    if s3_client is None:
        s3_client, s3_resource = get_s3_client()

    key_chunks = []
    for i in range(0, len(keys), chunk_size):
        chunk = []
        for key in (list(keys)[i:i+100]):
            chunk.append({'Key': key})
        key_chunks.append(chunk)
    for chunk in key_chunks:
        s3_client.delete_objects(
            Bucket=aws_bucket_name,
            Delete={'Objects': chunk})


class BasePublishCommand(BaseCommand):
    """
    Base command that exposes these utility methods to the Management
    Commands that need them.
    """

    def get_s3_client(self):
        return get_s3_client()

    def get_all_objects_in_bucket(self, *args, **kwargs):
        return get_all_objects_in_bucket(*args, **kwargs)

    def batch_delete_s3_objects(self, *args, **kwargs):
        return batch_delete_s3_objects(*args, **kwargs)
