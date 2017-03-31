import os
import time
import hashlib
import logging
import mimetypes

from django.conf import settings
from multiprocessing.pool import ThreadPool
from bakery import DEFAULT_GZIP_CONTENT_TYPES
from bakery.management.commands import (
    BasePublishCommand,
    get_s3_client
)
from django.core.urlresolvers import get_callable
from django.core.management.base import CommandError
logger = logging.getLogger(__name__)


class Command(BasePublishCommand):
    help = "Syncs the build directory with Amazon s3 bucket"

    # Default permissions for the files published to s3
    DEFAULT_ACL = 'public-read'

    # Error messages we might use below
    build_missing_msg = "Build directory does not exist. Cannot publish something before you build it."
    build_unconfig_msg = "Build directory unconfigured. Set BUILD_DIR in settings.py or provide it with --build-dir"
    bucket_unconfig_msg = "Bucket unconfigured. Set AWS_BUCKET_NAME in settings.py or provide it with --aws-bucket-name"
    views_unconfig_msg = "Bakery views unconfigured. Set BAKERY_VIEWS in settings.py or provide a list as arguments."

    def add_arguments(self, parser):
        parser.add_argument(
            "--build-dir",
            action="store",
            dest="build_dir",
            default='',
            help="Specify the path of the build directory. Will use settings.BUILD_DIR by default."
        )
        parser.add_argument(
            "--aws-bucket-name",
            action="store",
            dest="aws_bucket_name",
            default='',
            help="Specify the AWS bucket to sync with. Will use settings.AWS_BUCKET_NAME by default."
        )
        parser.add_argument(
            "--force",
            action="store_true",
            dest="force",
            default="",
            help="Force a republish of all items in the build directory"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default="",
            help="Display the output of what would have been uploaded removed, but without actually publishing."
        )
        parser.add_argument(
            "--no-delete",
            action="store_true",
            dest="no_delete",
            default=False,
            help=("Keep files in S3, even if they do not exist in the build directory.")
        )
        parser.add_argument(
            "--no-pooling",
            action="store_true",
            dest="no_pooling",
            default=False,
            help=("Run uploads one by one rather than pooling them to run concurrently.")
        )

    def handle(self, *args, **options):
        """
        Sync files in the build directory to a specified S3 bucket
        """
        # Counts and such we can use to keep tabs on this as they progress
        self.uploaded_files = 0
        self.uploaded_file_list = []
        self.deleted_files = 0
        self.deleted_file_list = []
        self.start_time = time.time()

        # Configure all the options we're going to use
        self.set_options(options)

        # Initialize the boto connection
        self.s3_client, self.s3_resource = get_s3_client()

        # Grab our bucket
        self.bucket = self.s3_resource.Bucket(self.aws_bucket_name)

        # Get a list of all keys in our s3 bucket
        self.s3_obj_dict = self.get_all_objects_in_bucket(
            self.aws_bucket_name,
            self.s3_client
        )

        # Get a list of all the local files in our build directory
        self.local_file_list = self.get_local_file_list()

        # Sync the two
        self.sync_with_s3()

        # Delete anything that's left in our keys dict
        if not self.dry_run and not self.no_delete:
            self.deleted_file_list = list(self.s3_obj_dict.keys())
            self.deleted_files = len(self.deleted_file_list)
            if self.deleted_files:
                if self.verbosity > 0:
                    logger.debug("deleting %s keys" % self.deleted_files)
                self.batch_delete_s3_objects(
                    self.deleted_file_list,
                    self.aws_bucket_name
                )

        # Run any post publish hooks on the views
        if not hasattr(settings, 'BAKERY_VIEWS'):
            raise CommandError(self.views_unconfig_msg)
        for view_str in settings.BAKERY_VIEWS:
            view = get_callable(view_str)()
            if hasattr(view, 'post_publish'):
                getattr(view, 'post_publish')(self.bucket)

        # We're finished, print the final output
        elapsed_time = time.time() - self.start_time
        if self.verbosity > 0:
            msg = "publish completed, %d uploaded and %d deleted files in %.2f seconds" % (
                self.uploaded_files,
                self.deleted_files,
                elapsed_time
            )
            self.stdout.write(msg)
            logger.info(msg)

        if self.verbosity > 2:
            for f in self.uploaded_file_list:
                logger.info("updated file: %s" % f)
            for f in self.deleted_file_list:
                logger.info("deleted file: %s" % f)

        if self.dry_run:
            logger.info("publish executed with the --dry-run option. No content was changed on S3.")

    def set_options(self, options):
        """
        Configure all the many options we'll need to make this happen.
        """
        self.verbosity = int(options.get('verbosity'))

        # Will we be gzipping?
        self.gzip = getattr(settings, 'BAKERY_GZIP', False)

        # And if so what content types will we be gzipping?
        self.gzip_content_types = getattr(
            settings,
            'GZIP_CONTENT_TYPES',
            DEFAULT_GZIP_CONTENT_TYPES
        )

        # What ACL (i.e. security permissions) will be giving the files on S3?
        self.acl = getattr(settings, 'DEFAULT_ACL', self.DEFAULT_ACL)

        # Should we set cache-control headers?
        self.cache_control = getattr(settings, 'BAKERY_CACHE_CONTROL', {})

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
            if self.verbosity > 0:
                logger.info("executing with the --dry-run option set.")
        else:
            self.dry_run = False

        self.no_delete = options.get('no_delete')
        self.no_pooling = options.get('no_pooling')

    def get_local_file_list(self):
        """
        Walk the local build directory and create a list of relative and
        absolute paths to files.
        """
        file_list = []
        for (dirpath, dirnames, filenames) in os.walk(self.build_dir):
            for fname in filenames:
                # relative path, to sync with the S3 key
                local_key = os.path.join(
                    os.path.relpath(dirpath, self.build_dir),
                    fname
                )
                if local_key.startswith('./'):
                    local_key = local_key[2:]
                file_list.append(local_key)
        return file_list

    def sync_with_s3(self):
        """
        Walk through our self.local_files list, and match them with the list
        of keys in the S3 bucket.
        """
        # Create a list to put all the files we're going to update
        update_list = []

        for file_key in self.local_file_list:
            # store a reference to the absolute path, if we have to open it
            abs_file_path = os.path.join(self.build_dir, file_key)

            # check if the file exists
            if file_key in self.s3_obj_dict:
                s3_etag = self.s3_obj_dict[file_key].get('ETag').strip('"')
                local_md5 = hashlib.md5(
                    open(abs_file_path, "rb").read()
                ).hexdigest()

                # don't upload if the md5 sums are the same
                if s3_etag == local_md5 and not self.force_publish:
                    pass
                elif self.force_publish:
                    update_list.append((file_key, abs_file_path))
                else:
                    update_list.append((file_key, abs_file_path))

                # remove the file from the dict, we don't need it anymore
                del self.s3_obj_dict[file_key]

            # if the file doesn't exist, create it
            else:
                update_list.append((file_key, abs_file_path))

        # Upload all these files
        if self.no_pooling:
            [self.upload_to_s3(*u) for u in update_list]
        else:
            pool = ThreadPool(processes=10)
            pool.map(self.pooled_upload_to_s3, update_list)

    def pooled_upload_to_s3(self, payload):
        """
        A passthrough for our ThreadPool because it can't take two arguments.

        So all we're doing here is split the list into args for the real
        upload function.
        """
        self.upload_to_s3(*payload)

    def upload_to_s3(self, key, filename):
        """
        Set the content type and gzip headers if applicable
        and upload the item to S3
        """
        extra_args = {'ACL': self.acl}
        # guess and add the mimetype to header
        content_type = mimetypes.guess_type(filename)[0]

        if content_type:
            extra_args['ContentType'] = content_type

        # add the gzip headers, if necessary
        if self.gzip and content_type in self.gzip_content_types:
            extra_args['ContentEncoding'] = 'gzip'

        # add the cache-control headers if necessary
        if content_type in self.cache_control:
            extra_args['CacheControl'] = ''.join((
                'max-age=',
                str(self.cache_control[content_type])
            ))

        # access and write the contents from the file
        if not self.dry_run:
            if self.verbosity > 0:
                logger.debug("uploading %s" % filename)
            s3_obj = self.s3_resource.Object(self.aws_bucket_name, key)
            s3_obj.upload_file(filename, ExtraArgs=extra_args)
        self.uploaded_files += 1
        self.uploaded_file_list.append(filename)
