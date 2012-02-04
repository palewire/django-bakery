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

        try:
            settings.BAKERY_VIEWS
        except AttributeError:
            raise AttributeError("No views in settings.BAKERY_VIEWS")

        for view_str in settings.BAKERY_VIEWS:
            view = self._view_from_string(view_str)()
            view.build_queryset()
        
        # Build 404 page
        self.stdout.write("Building 404 page\n")
        rf = RequestFactory()
        response = render(rf.get("/404.html"), '404.html', {})
        self.write('404.html', response.content)

    def _view_from_string(self, name):
        """
        Takes a full string representing a dot-path to 
        a class (eg "blog.views.DetailView") and returns that
        class as a Python object.
        """
        mod = __import__(name.split('.')[0])
        bits = name.split('.')[1:]
        c = mod
        for bit in bits:
            c = getattr(c, bit)
        return c
