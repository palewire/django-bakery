import logging
from django.conf import settings
from django.core.management.base import CommandError
from bakery.management.commands import BasePublishCommand
logger = logging.getLogger(__name__)


class Command(BasePublishCommand):
    help = "Empties the Amazon S3 bucket defined in settings.py"
    bucket_unconfig_msg = "Bucket unconfigured. Set AWS_BUCKET_NAME in settings.py or provide it with --aws-bucket-name"

    def add_arguments(self, parser):
        parser.add_argument(
            "--aws-bucket-name",
            action="store",
            dest="aws_bucket_name",
            default='',
            help="Specify the AWS bucket to sync with. Will use settings.AWS_BUCKET_NAME by default."
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
        all_objects = self.get_all_objects_in_bucket(aws_bucket_name)
        keys = all_objects.keys()
        self.batch_delete_s3_objects(keys, aws_bucket_name)

        # A little logging
        logger.info("unpublish completed, %d deleted files" % len(keys))
