import os
import logging
from django.conf import settings
from bakery.views import BuildableMixin
from django.test.client import RequestFactory
from django.contrib.syndication.views import Feed
logger = logging.getLogger(__name__)


class BuildableFeed(Feed, BuildableMixin):
    """
    Extends the base Django Feed class to be buildable.
    """
    build_path = 'feed.xml'

    def get_content(self):
        return self(self.request).content

    @property
    def build_method(self):
        return self.build_queryset

    def build_queryset(self):
        logger.debug("Building %s" % self.build_path)
        self.request = RequestFactory().get(self.build_path)
        self.prep_directory(self.build_path)
        path = os.path.join(settings.BUILD_DIR, self.build_path)
        self.build_file(path, self.get_content())
