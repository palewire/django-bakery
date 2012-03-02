import os
import shutil
from django.conf import settings
from django.core import management
from django.shortcuts import render
from django.test.client import RequestFactory
from django.core.urlresolvers import get_callable
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Bake out the entire site as flat files in the build directory'
    
    def write(self, path, data):
        outfile = open(os.path.join(settings.BUILD_DIR, path), 'w')
        outfile.write(data)
        outfile.close()
    
    def handle(self, *args, **options):
        """
        Making it happen.
        """
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
        if os.path.exists(settings.MEDIA_ROOT):
            shutil.copytree(
                settings.MEDIA_ROOT,
                media_path
            )
        if os.path.exists(settings.STATIC_ROOT):
            shutil.copytree(settings.STATIC_ROOT, static_path)
        
        # Build views
        try:
            settings.BAKERY_VIEWS
        except AttributeError:
            raise CommandError("No views in settings.BAKERY_VIEWS")
        
        for view_str in settings.BAKERY_VIEWS:
            self.stdout.write("Building %s\n" % view_str)
            view = get_callable(view_str)
            view().build_method()
        
        # Build 404 page
        self.stdout.write("Building 404 page\n")
        rf = RequestFactory()
        response = render(rf.get("/404.html"), '404.html', {})
        self.write('404.html', response.content)

