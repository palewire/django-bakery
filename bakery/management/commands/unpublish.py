import os
import random
import string
import shutil
import subprocess
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Empties the Amazon S3 bucket defined in settings.py"
    
    def get_random_string(self, length=6):
        """
        Generate a random string of letters and numbers
        """
        return ''.join(random.choice(string.letters + string.digits) for i in xrange(length))
    
    def handle(self, *args, **kwds):
        tmp_path = './tmp-%s' % self.get_random_string()
        os.mkdir(tmp_path)
        cmd = "s3cmd sync --delete %s/ s3://%s"
        subprocess.call(cmd % (tmp_path, settings.AWS_BUCKET_NAME), shell=True)
        shutil.rmtree(tmp_path)

