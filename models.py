"""
Models that inherit from Django's and add methods that 
make it convenient for building out flat files. The building
magic here really relies on your view being class-based
and having a build_object method, like the BuildableDetailView 
included in this app.
"""

from django.db import models

class BuildableModel(models.Model):
    """
    An abstract base model for an object that builds out
    its own detail pages. 

    Set the detail_view to the string representing your class-based
    view (which should inherit from BuildableDetailView), then fill
    out _build_related and _build_extra if need be.
    """
    detail_view = None

    def _view_from_string(name):
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

    def _build_related(self):
        """
        Builds related content, such as an RSS feed.
        """
        pass

    def _build_extra(self):
        """
        Build extra content, like copying an image to
        a thumbnails folder under the media folder.
        """
        pass

    def build(self):
        """
        Takes the view pointed to by self.detail_view,
        runs build_object with `self`, and calls 
        _build_extra() and _build_related()
        """
        view = self._view_from_string(self.detail_view)
        view().build_object(self)
        self._build_extra()
        self._build_related()

    def get_absolute_url(self):
        pass

    class Meta:
        abstract=True
