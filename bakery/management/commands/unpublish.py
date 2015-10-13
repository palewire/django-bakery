import boto
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Empties the Amazon S3 bucket defined in settings.py"

    def handle(self, *args, **kwds):
        # Use a non-standard calling format, if one is specified
        s3_calling_format = getattr(
            settings,
            'BAKERY_S3_CALLING_FORMAT',
            boto.s3.connection.S3Connection.DefaultCallingFormat
        )

        # Allow the user to specify a non-standard S3 endpoint
        s3_host = getattr(
            settings,
            'BAKERY_S3_HOST',
            boto.s3.connection.S3Connection.DefaultHost
        )

        conn = boto.connect_s3(settings.AWS_ACCESS_KEY_ID,
                               settings.AWS_SECRET_ACCESS_KEY,
                               host=s3_host,
                               calling_format=s3_calling_format)
        self.bucket = conn.get_bucket(settings.AWS_BUCKET_NAME)
        self.keys = list(key.name for key in self.bucket.list())
        # Break list of keys to delete into list of lists, each with 100 keys
        self.key_chunks = []
        for i in range(0, len(self.keys), 100):
            self.key_chunks.append(self.keys[i:i+100])
        for chunk in self.key_chunks:
            self.bucket.delete_keys(chunk)
