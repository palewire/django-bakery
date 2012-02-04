import os
import subprocess
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Syncs the build directory with the Amazon S3 bucket defined in settings.py"
    
    def handle(self, *args, **kwds):
        if not os.path.exists(settings.BUILD_DIR):
            raise CommandError("Build directory does not exist. Cannot publish something before you build it.")
        cmd = "s3cmd sync --delete-removed --acl-public %s/ s3://%s"
        subprocess.call(cmd % (settings.BUILD_DIR, settings.AWS_BUCKET_NAME),
            shell=True)
