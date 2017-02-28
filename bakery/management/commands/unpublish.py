import boto3
import logging
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from bakery.s3_utils import get_all_objects_in_bucket, batch_delete_s3_objects
logger = logging.getLogger(__name__)

s3 = boto3.resource('s3')


class Command(BaseCommand):
    help = "Empties the Amazon S3 bucket defined in settings.py"
    bucket_unconfig_msg = "AWS bucket name unconfigured. Set AWS_BUCKET_NAME \
in settings.py or provide it with --aws-bucket-name"

    def add_arguments(self, parser):
        parser.add_argument(
            "--aws-bucket-name",
            action="store",
            dest="aws_bucket_name",
            default='',
            help="Specify the AWS bucket to sync with. \
                Will use settings.AWS_BUCKET_NAME by default."
        )

    def handle(self, *args, **options):
        if options.get("aws_bucket_name"):
            aws_bucket_name = options.get("aws_bucket_name")
        else:
            # Otherwise try to find it the settings
            if not hasattr(settings, 'AWS_BUCKET_NAME'):
                raise CommandError(self.bucket_unconfig_msg)
            aws_bucket_name = settings.AWS_BUCKET_NAME

        # Pull all the keys from the bucket
        all_objects = get_all_objects_in_bucket(aws_bucket_name)
        keys = all_objects.keys()
        batch_delete_s3_objects(keys, aws_bucket_name)

        # A little logging
        logger.info("unpublish completed, %d deleted files" % len(keys))
