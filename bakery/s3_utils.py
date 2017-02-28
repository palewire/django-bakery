import os
import boto3

from django.conf import settings

s3 = boto3.resource('s3')


def get_s3_client():
    access_key = os.environ.get('AWS_ACCESS_KEY_ID', '')
    if hasattr(settings, 'AWS_ACCESS_KEY_ID'):
        access_key = settings.AWS_ACCESS_KEY_ID

    secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
    if hasattr(settings, 'AWS_SECRET_ACCESS_KEY'):
        secret_key = settings.AWS_SECRET_ACCESS_KEY

    session = boto3.setup_default_session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key)
    return boto3.client('s3')


def get_all_objects_in_bucket(aws_bucket_name, s3_client=None, max_keys=1000):
    if not s3_client:
        s3_client = get_s3_client()

    obj_dict = {}
    continuation_token = ''
    while True:
        kwargs = {'Bucket': aws_bucket_name, 'MaxKeys': max_keys}
        if continuation_token:
            kwargs['ContinuationToken'] = continuation_token
        list_objects_response = s3_client.list_objects_v2(**kwargs)
        for obj in list_objects_response.get('Contents', []):
            obj_dict[obj.get('Key')] = obj

        if not list_objects_response.get('IsTruncated'):
            break

        continuation_token = list_objects_response.get('NextContinuationToken')

    return obj_dict


def batch_delete_s3_objects(
        keys, aws_bucket_name, chunk_size=100, s3_client=None):
    if s3_client is None:
        s3_client = get_s3_client()

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
