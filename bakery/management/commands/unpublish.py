import boto
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Empties the Amazon S3 bucket defined in settings.py"

    def handle(self, *args, **kwds):
        conn = boto.connect_s3(settings.AWS_ACCESS_KEY_ID,
                               settings.AWS_SECRET_ACCESS_KEY)
        self.bucket = conn.get_bucket(settings.AWS_BUCKET_NAME)
        self.keys = list(key.name for key in self.bucket.list())
        self.bucket.delete_keys(self.keys)
