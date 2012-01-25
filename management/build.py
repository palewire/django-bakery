import os
import shutil
from django.conf import settings
from optparse import make_option
from django.core import management
from django.shortcuts import render
from django.test.client import RequestFactory
from django.core.management.base import BaseCommand, CommandError
from django.core.urlresolvers import reverse


class Command(BaseCommand):
    help = 'Bake out the entire site as flat files in the build directory'
    
    def write(self, path, data):
        outfile = open(os.path.join(settings.BUILD_DIR, path), 'w')
        outfile.write(data)
        outfile.close()
    
    def handle(self, *args, **options):
        # Destroy the build directory, if it exists
        self.stdout.write("Creating build directory\n")
        if os.path.exists(settings.BUILD_DIR):
            shutil.rmtree(settings.BUILD_DIR)
        # Then recreate it from scratch
        os.makedirs(settings.BUILD_DIR)
        
        # Build up static files
        management.call_command("collectstatic", interactive=False, verbosity=0)
        
        # Copy the media directory
        self.stdout.write("Building static media\n")
        media_path = os.path.join(settings.BUILD_DIR, 'media')
        static_path = os.path.join(settings.BUILD_DIR, 'static')
        os.path.exists(media_path) or shutil.copytree(
            settings.MEDIA_ROOT,
            media_path
        )
        shutil.copytree(settings.STATIC_ROOT, static_path)

        # CURRENT IDEA:
        # Here we should parse through a list of views passed in 
        # from the command line, and then run .build_objects()
        # over them. That way we can use the built-in queryset.
        #
        
        # Build 404 page
        self.stdout.write("Building 404 page\n")
        rf = RequestFactory()
        response = render(rf.get("/404.html"), '404.html', {})
        self.write('404.html', response.content)
