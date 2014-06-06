import os
import boto
import time
import hashlib
import logging
import mimetypes
from django.conf import settings
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
logger = logging.getLogger(__name__)


custom_options = (
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
        help="Specify the AWS bucket to sync with. \
Will use settings.AWS_BUCKET_NAME by default."
    ),
    make_option(
        "--force",
        action="store_true",
        dest="force",
        default="",
        help="Force a republish of all items in the build directory"
    ),
    make_option(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        default="",
        help="Display the output of what would have been uploaded \
removed, but without actually publishing."
    ),
)


class Command(BaseCommand):
    help = "Syncs the build directory with Amazon s3 bucket"
    option_list = BaseCommand.option_list + custom_options

    # Default permissions for the files published to s3
    DEFAULT_ACL = 'public-read'

    # Mimetypes of content we want to gzip
    GZIP_CONTENT_TYPES = (
        'text/css',
        'text/html',
        'application/javascript',
        'application/x-javascript',
        'application/json',
        'application/xml'
    )

    # Error messages we might use below
    build_missing_msg = "Build directory does not exist. Cannot publish \
something before you build it."
    build_unconfig_msg = "Build directory unconfigured. Set BUILD_DIR in \
settings.py or provide it with --build-dir"
    bucket_unconfig_msg = "AWS bucket name unconfigured. Set AWS_BUCKET_NAME \
in settings.py or provide it with --aws-bucket-name"

    def handle(self, *args, **options):
        """
        Sync files in the build directory to a specified S3 bucket
        """
        self.set_options(options)

        # initialize the boto connection, grab the bucket
        # and make a dict out of the results object from bucket.list()
        conn = boto.connect_s3(settings.AWS_ACCESS_KEY_ID,
                               settings.AWS_SECRET_ACCESS_KEY)
        self.bucket = conn.get_bucket(self.aws_bucket_name)
        self.keys = dict((key.name, key) for key in self.bucket.list())

        self.local_files = self.build_local_files_list()
        self.sync_s3()

        # delete anything that's left in our keys dict
        for key in self.keys:
            logger.debug("deleting file %s" % key)
            if not self.dry_run:
                self.bucket.delete_key(key)
            self.deleted_files += 1

        # we're finished, print the final output
        elapsed_time = time.time() - self.start_time
        logger.info("publish completed, %d uploaded and %d deleted files \
in %.2f seconds" % (self.uploaded_files, self.deleted_files, elapsed_time))

        if self.dry_run:
            logger.info("publish executed with the --dry-run option. \
No content was changed on S3.")

    def set_options(self, options):
        """
        Configure all the many options we'll need to make this happen.
        """
        # Counts and such we can use to keep tabs on this as they progress
        self.uploaded_files = 0
        self.deleted_files = 0
        self.start_time = time.time()

        # Will we be gzipping?
        self.gzip = getattr(settings, 'BAKERY_GZIP', False)

        # And if so what content types will we be gzipping?
        self.gzip_content_types = getattr(
            settings,
            'GZIP_CONTENT_TYPES',
            GZIP_CONTENT_TYPES
        )

        # What ACL (i.e. security permissions) will be giving the files on S3?
        self.acl = getattr(settings, 'DEFAULT_ACL', DEFAULT_ACL)

        # If the user specifies a build directory...
        if options.get('build_dir'):
            # ... validate that it is good.
            if not os.path.exists(options.get('build_dir')):
                raise CommandError(self.build_missing_msg)
            # Go ahead and use it
            self.build_dir = options.get("build_dir")
        # If the user does not specify a build dir...
        else:
            # Check if it is set in settings.py
            if not hasattr(settings, 'BUILD_DIR'):
                raise CommandError(self.build_unconfig_msg)
            # Then make sure it actually exists
            if not os.path.exists(settings.BUILD_DIR):
                raise CommandError(self.build_missing_msg)
            # Go ahead and use it
            self.build_dir = settings.BUILD_DIR

        # If the user provides a bucket name, use that.
        if options.get("aws_bucket_name"):
            self.aws_bucket_name = options.get("aws_bucket_name")
        else:
            # Otherwise try to find it the settings
            if not hasattr(settings, 'AWS_BUCKET_NAME'):
                raise CommandError(self.bucket_unconfig_msg)
            self.aws_bucket_name = settings.AWS_BUCKET_NAME

        # If the user sets the --force option
        if options.get('force'):
            self.force_publish = True
        else:
            self.force_publish = False

        # set the --dry-run option
        if options.get('dry_run'):
            self.dry_run = True
            logger.info("Executing with the --dry-run option set.")
        else:
            self.dry_run = False

    def upload_s3(self, key, filename):
        """
        Set the content type and gzip headers if applicable
        and upload the item to S3
        """
        headers = {}

        # guess and add the mimetype to header
        content_type = mimetypes.guess_type(filename)[0]
        headers['Content-Type'] = content_type

        # add the gzip headers, if necessary
        if self.gzip and content_type in self.gzip_content_types:
            headers['Content-Encoding'] = 'gzip'

        # access and write the contents from the file
        with open(filename, 'rb') as file_obj:
            if not self.dry_run:
                key.set_contents_from_file(file_obj, headers, policy=self.acl)
            self.uploaded_files += 1

    def build_local_files_list(self):
        """
        Walk the local build directory and create a list
        of relative and absolute paths to files.
        This will be used to sync against the S3 bucket list.
        """
        files_list = []

        for (dirpath, dirnames, filenames) in os.walk(self.build_dir):

            for fname in filenames:
                # relative path, to sync with the S3 key
                local_key = os.path.join(os.path.relpath(dirpath,
                                         self.build_dir), fname)
                if local_key.startswith('./'):
                    local_key = local_key[2:]
                files_list.append(local_key)

        return files_list

    def sync_s3(self):
        """
        Walk through our self.local_files list, and match them with the list
        of keys in the S3 bucket.
        """

        for file_key in self.local_files:
            # store a reference to the absolute path, if we have to open it
            abs_file_path = os.path.join(self.build_dir, file_key)

            # check if the file exists
            if file_key in self.keys:
                key = self.keys[file_key]
                s3_md5 = key.etag.strip('"')
                local_md5 = hashlib.md5(
                    open(abs_file_path, "rb").read()
                    ).hexdigest()

                # don't upload if the md5 sums are the same
                if s3_md5 == local_md5 and not self.force_publish:
                    pass
                elif self.force_publish:
                    logger.debug("forcing update of file %s" % file_key)
                    self.upload_s3(key, abs_file_path)
                else:
                    logger.debug("updating file %s" % file_key)
                    self.upload_s3(key, abs_file_path)

                # remove the file from the dict, we don't need it anymore
                del self.keys[file_key]

            # if the file doesn't exist, create it
            else:
                logger.debug("creating file %s" % file_key)
                if not self.dry_run:
                    key = self.bucket.new_key(file_key)
                self.upload_s3(key, abs_file_path)
