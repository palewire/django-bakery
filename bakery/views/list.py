"""
Views that inherit from Django's class-based generic views and add methods
for building flat files.
"""
import logging
from fs import path
from .base import BuildableMixin
from django.conf import settings
from django.views.generic import ListView
logger = logging.getLogger(__name__)


class BuildableListView(ListView, BuildableMixin):
    """
    Render and builds a page about a list of objects.

    Required attributes:

        model or queryset:
            Where the list of objects should come from. `self.queryset` can
            be any iterable of items, not just a queryset.

        build_path:
            The target location of the built file in the BUILD_DIR.
            `index.html` would place it at the built site's root.
            `foo/index.html` would place it inside a subdirectory.
            `index.html is the default.

        template_name:
            The name of the template you would like Django to render. You need
            to override this if you don't want to rely on the Django defaults.

    Pagination is handled like a django ListView, and templates should be
    designed in the same way.
    When pagination is enabled the default build locations for the first page
    are: build_folder/build_path and /build_folder/build_page_name/1/build_path,
    with other pages only built in:
    /build_folder/build_page_name/<page_number>/build_path
    """
    build_folder = ''
    build_page_name = "page"
    build_path = 'index.html'


    @property
    def build_method(self):
        if self.get_paginate_by(self.queryset):
            return self.build_pagination
        else:
            return self.build_queryset

    def build_pagination(self):
        """
        If pagination is enabled, build the queryset for each page.
        """
        number_of_pages = math.ceil(len(self.queryset) / self.paginate_by)
        if not hasattr(self, "kwargs"):
            self.kwargs = {}
        for page in range(0, number_of_pages + 1):
            self.kwargs['page'] = page
            self.build_queryset()

    def get_page_build_path(self):
        """
        Create the path to build each page in pagination
        Defaults to building in:
        <build_folder>/<build_page_name>/<page>/<build_path>
        The current page is held in self.kwargs['page']
        """
        build_path = path.join( self.build_folder,
                                self.build_page_name,
                                str(self.kwargs['page']),
                                self.build_path)
        return build_path

    def get_build_path(self):
        build_path = ''
        if self.get_paginate_by(self.queryset):
            build_path = self.get_page_build_path()
        else:
            build_path = path.join(self.build_folder, self.build_path)
        return build_path


    def build_queryset(self):
        logger.debug("Building %s" % self.get_build_path())
        self.request = self.create_request(self.get_build_path())
        self.prep_directory(self.get_build_path())
        target_path = path.join(settings.BUILD_DIR, self.get_build_path())
        self.build_file(target_path, self.get_content())
