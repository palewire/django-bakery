import os
import six
import logging
import subprocess
from django.conf import settings
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
logger = logging.getLogger(__name__)


custom_options = (
    make_option(
        "--config",
        action="store",
        dest="config",
        default='',
        help="Specify the path of an s3cmd configuration file. \
Will use ~/.s3cmd by default."
    ),
    make_option(
        "--build-dir",
        action="store",
        dest="build_dir",
        default='',
        help="Specify the path of the build directory. \
Will use settings.BUILD_DIR by default."
    ),
    make_option(
        "--aws-bucket-name",
        action="store",
        dest="aws_bucket_name",
        default='',
        help="Specify the AWS bucket to synce with. \
Will use settings.AWS_BUCKET_NAME by default."
    ),
)


class Command(BaseCommand):
    help = "Syncs the build directory with Amazon S3 bucket using s3cmd"
    option_list = BaseCommand.option_list + custom_options
    build_missing_msg = "Build directory does not exist. Cannot publish \
something before you build it."
    build_unconfig_msg = "Build directory unconfigured. Set BUILD_DIR in \
settings.py or provide it with --build-dir"
    bucket_unconfig_msg = "AWS bucket name unconfigured. Set AWS_BUCKET_NAME \
in settings.py or provide it with --aws-bucket-name"

    def sync(self, cmd, options):
        # If the user specifies a build directory...
        if options.get('build_dir'):
            # ... validate that it is good.
            if not os.path.exists(options.get('build_dir')):
                raise CommandError(self.build_missing_msg)
            # Go ahead of use it
            self.build_dir = options.get("build_dir")
        # If the user does not specify a build dir...
        else:
            # Check if it is set in settings.py
            if not hasattr(settings, 'BUILD_DIR'):
                raise CommandError(self.build_unconfig_msg)
            # Then make sure it actually exists
            if not os.path.exists(settings.BUILD_DIR):
                raise CommandError(self.build_missing_msg)
            # Go ahead of use it
            self.build_dir = settings.BUILD_DIR

        # Append the build dir to our basic s3cmd command
        cmd += " %s/" % self.build_dir

        # If the user has specified a custom config path append that
        if options.get('config'):
            cmd += ' --config=%(config)s' % options

        # If the user provides a bucket name, use that.
        if options.get("aws_bucket_name"):
            self.aws_bucket_name = options.get("aws_bucket_name")
        else:
            # Otherwise try to find it the settings
            if not hasattr(settings, 'AWS_BUCKET_NAME'):
                raise CommandError(self.bucket_unconfig_msg)
            self.aws_bucket_name = settings.AWS_BUCKET_NAME

        # Append the AWS bucket name to the command
        cmd += ' s3://%s' % self.aws_bucket_name

        # Print out the command unless verbosity is above the default
        logger.debug('Executing %s' % cmd)
        if int(options.get('verbosity')) > 1:
            six.print_('Executing %s' % cmd)

        # Execute the command
        subprocess.call(cmd, shell=True)

    # gzip the rendered html views, sitemaps, and any static css, js and json
    def sync_gzipped_files(self, options):
        gzip_file_match = getattr(
            settings,
            'GZIP_FILE_MATCH',
            '(\.html|\.xml|\.css|\.js|\.json)$'
        )
        cmd = "s3cmd sync --exclude '*.*' --rinclude '%s' " % gzip_file_match
        cmd += "--add-header='Content-Encoding: gzip' --acl-public"
        self.sync(cmd, options)

    # The s3cmd basic command, before we append all the options.
    def sync_all_files(self, options):
        cmd = "s3cmd sync --delete-removed --acl-public"
        self.sync(cmd, options)

    def handle(self, *args, **options):
        """
        Cobble together s3cmd command with all the proper options and run it.
        """
        logger.info("Publish started")

        # sync gzipped files, if not opted out
        if getattr(settings, 'BAKERY_GZIP', False):
            self.sync_gzipped_files(options)

        # sync the rest of the files
        self.sync_all_files(options)
