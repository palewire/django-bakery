import boto
import logging
from django.conf import settings
from django.core.management.base import BaseCommand
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Empties the Amazon S3 bucket defined in settings.py"

    def handle(self, *args, **options):
        # Pull all the keys from the bucket
        conn = boto.connect_s3(
            settings.AWS_ACCESS_KEY_ID,
            settings.AWS_SECRET_ACCESS_KEY
        )
        self.bucket = conn.get_bucket(settings.AWS_BUCKET_NAME)
        self.keys = list(key.name for key in self.bucket.list())

        # Break list of keys to delete into list of lists, each with 100 keys
        self.key_chunks = []
        for i in range(0, len(self.keys), 100):
            self.key_chunks.append(self.keys[i:i+100])
        for chunk in self.key_chunks:
            self.bucket.delete_keys(chunk)

        # A little logging
        logger.info("unpublish completed, %d deleted files" % len(self.keys))
