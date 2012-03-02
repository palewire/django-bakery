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

    @property
    def build_method(self):
        return self.build
    
    def build(self):
        logger.debug("Building %s" % self.template_name)
        self.request = RequestFactory().get(self.build_path)
        html = self.get(self.request).render().content
        path = os.path.join(settings.BUILD_DIR, self.build_path)
        # Make sure the directory exists
        dirname = os.path.dirname(self.build_path)
        if dirname:
            dirname = os.path.join(settings.BUILD_DIR, dirname)
            os.path.exists(dirname) or os.mkdir(dirname)
        # Write out the data
        outfile = open(path, 'w')
        outfile.write(html)
        outfile.close()


class BuildableListView(ListView):
    build_path = 'index.html'
    
    @property
    def build_method(self):
        return self.build_queryset
    
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
    
    @property
    def build_method(self):
        return self.build_queryset
    
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


class Buildable404View(BuildableTemplateView):
    """
    The default Django 404 page.
    """
    build_path = '404.html'
    template_name = '404.html'
