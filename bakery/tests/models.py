# C:/dev/git_clones/django-bakery/bakery/tests/models.py
from django.db import models

from bakery import models as bakery_models  # Use an alias to avoid confusion

# Note: The string "bakery.tests.views.MockDetailView" assumes MockDetailView
# will be defined in bakery/tests/views.py and that Django's app loading
# will make it discoverable by this path *after* setup.


class MockObject(bakery_models.BuildableModel):
    # Updated path if MockDetailView moves to bakery.tests.views
    detail_views = ["bakery.tests.views.MockDetailView"]
    name = models.CharField(max_length=500)
    pub_date = models.DateField()

    class Meta:
        app_label = "bakery_tests"  # Important for test models

    def get_absolute_url(self):
        # super().get_absolute_url()  # Just for test coverage
        return f"/{self.id}/"


class NoUrlObject(bakery_models.BuildableModel):
    # Updated path if MockDetailView moves to bakery.tests.views
    # detail_views = ["bakery.tests.views.MockDetailView"]
    name = models.CharField(max_length=500)
    pub_date = models.DateField()

    class Meta:
        app_label = "bakery_tests"


class AutoMockObject(bakery_models.AutoPublishingBuildableModel):
    # Updated path if MockDetailView moves to bakery.tests.views
    detail_views = ["bakery.tests.views.MockDetailView"]
    name = models.CharField(max_length=500)
    pub_date = models.DateField()
    is_published = models.BooleanField(default=False)

    class Meta:
        app_label = "bakery_tests"

    def get_absolute_url(self):
        return f"/{self.id}/"
