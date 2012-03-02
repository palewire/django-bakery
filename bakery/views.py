"""
Views that inherit from Django's class-based generic views and add methods 
for building flat files.
"""
import os
import logging
from django.conf import settings
from django.test.client import RequestFactory
from django.views.generic import TemplateView, DetailView, ListView

logger = logging.getLogger(__name__)


class BuildableTemplateView(TemplateView):
    """
    Renders and builds a simple template.
    
    When inherited, the child class should include the following attribuntes:
    
        build_path: 
            The target location of the built file in the BUILD_DIR. `index.html`
            would place it at the built site's root. `foo/index.html` would
            place it inside a subdirectory.
        
        template_name:
            The name of the template you would like Django to render.
    """

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
    """
    Render and builds a page about a list of objects.
    
    Required attributes:
     
        model or queryset:
            Where the list of objects should come from. `self.queryset` can 
            be any iterable of items, not just a queryset.
        
        build_path: 
            The target location of the built file in the BUILD_DIR. `index.html`
            would place it at the built site's root. `foo/index.html` would
            place it inside a subdirectory. `index.html is the default.
        
        template_name:
            The name of the template you would like Django to render. You need
            to override this if you don't want to rely on the Django defaults.
    """
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
    """
    Render and build a "detail" view of an object.
    
    Required attributes:
     
        queryset:
            the model instance the objects are looked up from.
        
        template_name:
            The name of the template you would like Django to render. You need
            to override this if you don't want to rely on the Django defaults.
    """
    @property
    def build_method(self):
        return self.build_queryset
    
    def write(self, path, data):
        outfile = open(path, 'w')
        outfile.write(data)
        outfile.close()
    
    def get_url(self, obj):
        """
        The URL at which the detail page should appear.
        """
        return obj.get_absolute_url()
    
    def get_build_path(self, obj):
        """
        Used to determine where to build the detail page. Override this if you
        would like your detail page at a different location. By default it
        will be built at get_url() + "index.html"
        """
        path = os.path.join(settings.BUILD_DIR, self.get_url(obj)[1:])
        os.path.exists(path) or os.makedirs(path)
        return os.path.join(path, 'index.html')
    
    def set_kwargs(self, obj):
        self.kwargs = {
            'pk': getattr(obj, 'pk', None),
            'slug': getattr(obj, self.get_slug_field(), None),
        }
    
    def get_html(self):
        """
        How to render the HTML for the detail page. If you choose to render
        using something other than a Django template, like HttpResponse for
        instance, you will want to override this.
        """
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
    The default Django 404 page, but built out.
    """
    build_path = '404.html'
    template_name = '404.html'
