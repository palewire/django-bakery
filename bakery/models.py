"""
Models that inherit from Django's and add methods that make it convenient for 
building out flat files.

The magic relies on your view being class-based and having a build_object
method, like the BuildableDetailView included in this app.
"""
from django.db import models


class BuildableModel(models.Model):
    """
    An abstract base model for an object that builds out
    its own detail pages. 

    Set `detail_views` to an iterable containing
    strings which represent your class-based
    view (which should inherit from BuildableDetailView), 
    then fill out _build_related and _build_extra if need be.
    """
    detail_views = []
    
    def _get_view(self, name):
        from django.core.urlresolvers import get_callable
        return get_callable(name)
    
    def _build_related(self):
        """
        Builds related content, such as an RSS feed.
        """
        pass
    
    def _build_extra(self):
        """
        Build extra content, like copying an image to a thumbnails folder under
        the media folder.
        """
        pass
    
    def build(self):
        """
        Iterates through the views pointed to by self.detail_views, runs
        build_object with `self`, and calls_build_extra() and _build_related().
        """
        for detail_view in self.detail_views:
            view = self._get_view(detail_view)
            view().build_object(self)
        self._build_extra()
        self._build_related()
    
    def get_absolute_url(self):
        pass
    
    class Meta:
        abstract=True
