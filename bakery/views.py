"""
Views that inherit from Django's class-based generic views
and add methods that make it convenient for building out 
flat files.
"""
import os
import logging
from django.conf import settings
from django.test.client import RequestFactory
from django.views.generic import TemplateView, DetailView, ListView

logger = logging.getLogger(__name__)


class BuildableTemplateView(TemplateView):

    def build_object(self, url):
        """
        Bake a template page as a flat HTML file.
        You need to pass it the relative URL in.
        """
        logger.debug("Building %s" % url)
        # Make a fake request
        self.request = RequestFactory().get(url)
        # Render the detail page HTML
        html = self.get(self.request).render().content
        # Create the path to save the flat file
        path = os.path.join(settings.BUILD_DIR, url[1:])
        os.path.exists(path) or os.makedirs(path)
        path = os.path.join(path, 'index.html')
        # Write out the data
        outfile = open(path, 'w')
        outfile.write(html)
        outfile.close()


class BuildableListView(ListView):
    """
    A list of all tables.
    """
    build_path = 'index.html'
    
    def build_queryset(self):
        logger.debug("Building %s" % self.build_path)
        # Make a fake request
        self.request = RequestFactory().get(self.build_path)
        # Make sure the directory exists
        dirname = os.path.dirname(self.build_path)
        if dirname:
            dirname = os.path.join(settings.BUILD_DIR, dirname)
            os.path.exists(dirname) or os.mkdir(dirname)
        # Render the list page as HTML
        html = self.get(self.request).render().content
        # Write it out to the appointed flat file
        path = os.path.join(settings.BUILD_DIR, self.build_path)
        outfile = open(path, 'w')
        outfile.write(html)
        outfile.close()


class BuildableDetailView(DetailView):
    
    def write(self, path, data):
        outfile = open(path, 'w')
        outfile.write(data)
        outfile.close()
    
    def get_url(self, obj):
        return obj.get_absolute_url()
    
    def get_build_path(self, obj):
        path = os.path.join(settings.BUILD_DIR, obj.get_absolute_url()[1:])
        os.path.exists(path) or os.makedirs(path)
        return os.path.join(path, 'index.html')
    
    def set_kwargs(self, obj):
        self.kwargs = {
            'pk': getattr(obj, 'pk', None),
            'slug': getattr(obj, self.get_slug_field(), None),
        }
    
    def get_html(self):
        return self.get(self.request).render().content
    
    def build_object(self, obj):
        logger.debug("Building %s" % obj)
        self.request = RequestFactory().get(self.get_url(obj))
        self.set_kwargs(obj)
        self.write(
            self.get_build_path(obj),
            self.get_html()
        )
    
    def build_queryset(self):
        [self.build_object(o) for o in self.queryset.all()]
