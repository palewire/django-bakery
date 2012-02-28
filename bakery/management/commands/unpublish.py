import os
import subprocess
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Syncs the build directory with the Amazon S3 bucket defined in settings.py"
    
    def handle(self, *args, **kwds):
        cmd = "s3cmd del s3://%s" % (
            os.path.join(settings.AWS_BUCKET_NAME, args[0])
        )
        subprocess.call(cmd, shell=True)

