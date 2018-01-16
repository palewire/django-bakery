import os
import time
import hashlib
import logging
import mimetypes
import multiprocessing
from django.conf import settings
from multiprocessing.pool import ThreadPool
from bakery import DEFAULT_GZIP_CONTENT_TYPES
from bakery.management.commands import (
    BasePublishCommand,
    get_s3_client,
    get_bucket_page
)
try:
    from django.core.urlresolvers import get_callable
except ImportError:  # Starting with Django 2.0, django.core.urlresolvers does not exist anymore
    from django.urls import get_callable
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
            "--aws-bucket-prefix",
            action="store",
            dest="aws_bucket_prefix",
            default='',
            help="Specify a prefix for the AWS bucket keys to sync with. None by default."
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
        logger.debug("Connecting to s3")
        if self.verbosity > 2:
            self.stdout.write("Connecting to s3")
        self.s3_client, self.s3_resource = get_s3_client()

        # Grab our bucket
        logger.debug("Retriving bucket {}".format(self.aws_bucket_name))
        if self.verbosity > 2:
            self.stdout.write("Retriving bucket {}".format(self.aws_bucket_name))
        self.bucket = self.s3_resource.Bucket(self.aws_bucket_name)

        # Get a list of all keys in our s3 bucket ...
        # ...nunless you're this is case where we're blindly pushing
        if self.force_publish and self.no_delete:
            self.blind_upload = True
            logger.debug("Skipping object retrieval. We won't need to because we're blinding uploading everything.")
            self.s3_obj_dict = {}
        else:
            self.blind_upload = False
            logger.debug("Retrieving objects now published in bucket")
            if self.verbosity > 2:
                self.stdout.write("Retrieving objects now published in bucket")
            self.s3_obj_dict = {}
            self.s3_obj_dict = self.get_bucket_file_list()

        # Get a list of all the local files in our build directory
        logger.debug("Retrieving files built locally")
        if self.verbosity > 2:
            self.stdout.write("Retrieving files built locally")
        self.local_file_list = self.get_local_file_list()

        # Sync local files with s3 bucket
        logger.debug("Syncing local files with bucket")
        if self.verbosity > 2:
            self.stdout.write("Syncing local files with bucket")
        self.sync_with_s3()

        # Delete anything that's left in our keys dict
        if not self.dry_run and not self.no_delete:
            self.deleted_file_list = list(self.s3_obj_dict.keys())
            self.deleted_files = len(self.deleted_file_list)
            if self.deleted_files:
                logger.debug("Deleting %s keys" % self.deleted_files)
                if self.verbosity > 0:
                    self.stdout.write("Deleting %s keys" % self.deleted_files)
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
        msg = "Publish completed, %d uploaded and %d deleted files in %.2f seconds" % (
            self.uploaded_files,
            self.deleted_files,
            elapsed_time
        )
        logger.info(msg)
        if self.verbosity > 0:
            self.stdout.write(msg)

        if self.dry_run:
            logger.info("Publish executed with the --dry-run option. No content was changed on S3.")
            if self.verbosity > 0:
                self.stdout.write("Publish executed with the --dry-run option. No content was changed on S3.")

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

        # The bucket prefix, if it exists
        self.aws_bucket_prefix = options.get("aws_bucket_prefix")

        # If the user sets the --force option
        if options.get('force'):
            self.force_publish = True
        else:
            self.force_publish = False

        # set the --dry-run option
        if options.get('dry_run'):
            self.dry_run = True
            if self.verbosity > 0:
                logger.info("Executing with the --dry-run option set.")
        else:
            self.dry_run = False

        self.no_delete = options.get('no_delete')
        self.no_pooling = options.get('no_pooling')

    def get_bucket_file_list(self):
        """
        Little utility method that handles pagination and returns
        all objects in given bucket.
        """
        logger.debug("Retrieving bucket object list")

        paginator = self.s3_client.get_paginator('list_objects')
        options = {
            'Bucket': self.aws_bucket_name
        }
        if self.aws_bucket_prefix:
            logger.debug("Adding prefix {} to bucket list as a filter".format(self.aws_bucket_prefix))
            options['Prefix'] = self.aws_bucket_prefix
        page_iterator = paginator.paginate(**options)

        obj_dict = {}
        for page in page_iterator:
            obj_dict.update(get_bucket_page(page))

        return obj_dict

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
        self.update_list = []

        # Figure out which files need to be updated and upload all these files
        logger.debug("Comparing {} local files with {} bucket files".format(
            len(self.local_file_list),
            len(self.s3_obj_dict.keys())
        ))
        if self.no_pooling:
            [self.compare_local_file(f) for f in self.local_file_list]
        else:
            cpu_count = multiprocessing.cpu_count()
            logger.debug("Pooling local file comparison on {} CPUs".format(cpu_count))
            pool = ThreadPool(processes=cpu_count)
            pool.map(self.compare_local_file, self.local_file_list)

        logger.debug("Uploading {} new or updated files to bucket".format(len(self.update_list)))
        if self.no_pooling:
            [self.upload_to_s3(*u) for u in self.update_list]
        else:
            logger.debug("Pooling s3 uploads on {} CPUs".format(cpu_count))
            pool = ThreadPool(processes=cpu_count)
            pool.map(self.pooled_upload_to_s3, self.update_list)

    def get_md5(self, filename):
        """
        Returns the md5 checksum of the provided file name.
        """
        with open(filename, 'rb') as f:
            m = hashlib.md5(f.read())
        return m.hexdigest()

    def get_multipart_md5(self, filename, chunk_size=8 * 1024 * 1024):
        """
        Returns the md5 checksum of the provided file name after breaking it into chunks.

        This is done to mirror the method used by Amazon S3 after a multipart upload.
        """
        # Loop through the file contents ...
        md5s = []
        with open(filename, 'rb') as fp:
            while True:
                # Break it into chunks
                data = fp.read(chunk_size)
                # Finish when there are no more
                if not data:
                    break
                # Generate a md5 hash for each chunk
                md5s.append(hashlib.md5(data))

        # Combine the chunks
        digests = b"".join(m.digest() for m in md5s)

        # Generate a new hash using them
        new_md5 = hashlib.md5(digests)

        # Create the ETag as Amazon will
        new_etag = '"%s-%s"' % (new_md5.hexdigest(), len(md5s))

        # Trim it down and pass it back for comparison
        return new_etag.strip('"').strip("'")

    def compare_local_file(self, file_key):
        """
        Compares a local version of a file with what's already published.

        If an update is needed, the file's key is added self.update_list.
        """
        # Where is the file?
        file_path = os.path.join(self.build_dir, file_key)

        # If we're in force_publish mode just add it
        if self.force_publish:
            self.update_list.append((file_key, file_path))
            # And quit now
            return

        # Does it exist in our s3 object list?
        if file_key in self.s3_obj_dict:

            # Get the md5 stored in Amazon's header
            s3_md5 = self.s3_obj_dict[file_key].get('ETag').strip('"').strip("'")

            # If there is a multipart ETag on S3, compare that to our local file after its chunked up.
            # We are presuming this file was uploaded in multiple parts.
            if "-" in s3_md5:
                local_md5 = self.get_multipart_md5(file_path)
            # Other, do it straight for the whole file
            else:
                local_md5 = self.get_md5(file_path)

            # If their md5 hexdigests match, do nothing
            if s3_md5 == local_md5:
                pass
            # If they don't match, we want to add it
            else:
                logger.debug("{} has changed".format(file_key))
                self.update_list.append((file_key, file_path))

            # Remove the file from the s3 dict, we don't need it anymore
            del self.s3_obj_dict[file_key]

        # If the file doesn't exist, queue it for creation
        else:
            logger.debug("{} has been added".format(file_key))
            self.update_list.append((file_key, file_path))

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
        # determine the mimetype of the file
        guess = mimetypes.guess_type(filename)
        content_type = guess[0]
        encoding = guess[1]

        if content_type:
            extra_args['ContentType'] = content_type

        # add the gzip headers, if necessary
        if (self.gzip and content_type in self.gzip_content_types) or encoding == 'gzip':
            extra_args['ContentEncoding'] = 'gzip'

        # add the cache-control headers if necessary
        if content_type in self.cache_control:
            extra_args['CacheControl'] = ''.join((
                'max-age=',
                str(self.cache_control[content_type])
            ))

        # access and write the contents from the file
        if not self.dry_run:
            logger.debug("Uploading %s" % filename)
            if self.verbosity > 0:
                self.stdout.write("Uploading %s" % filename)
            s3_obj = self.s3_resource.Object(self.aws_bucket_name, key)
            s3_obj.upload_file(filename, ExtraArgs=extra_args)

        # Update counts
        self.uploaded_files += 1
        self.uploaded_file_list.append(filename)
