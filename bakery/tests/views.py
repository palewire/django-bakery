# C:/dev/git_clones/django-bakery/bakery/tests/views.py
import json

from django.http import HttpResponse

from bakery import feeds as bakery_feeds  # Original feeds from the bakery app
from bakery import views as bakery_views  # Original views from the bakery app

# Import your mock models from the new location
from .models import MockObject, NoUrlObject  # AutoMockObject if needed by a view


# --- Mock Views ---
class MockDetailView(bakery_views.BuildableDetailView):
    model = MockObject
    slug_field = "the_slug"
    template_name = "detailview.html"


class NoUrlDetailView(bakery_views.BuildableDetailView):
    model = NoUrlObject


class MockArchiveIndexView(bakery_views.BuildableArchiveIndexView):
    model = MockObject
    date_field = "pub_date"
    template_name = "indexview.html"


class MockArchiveYearView(bakery_views.BuildableYearArchiveView):
    model = MockObject
    date_field = "pub_date"
    template_name = "yearview.html"


class MockArchiveMonthView(bakery_views.BuildableMonthArchiveView):
    model = MockObject
    date_field = "pub_date"
    month_format = "%m"
    template_name = "monthview.html"


class MockArchiveDayView(bakery_views.BuildableDayArchiveView):
    model = MockObject
    date_field = "pub_date"
    month_format = "%m"
    template_name = "dayview.html"


class MockRedirectView(bakery_views.BuildableRedirectView):
    build_path = "detail/badurl.html"
    url = "/detail/"


# --- Mock Feeds (can also live here or in a separate bakery/tests/feeds.py) ---
class MockRSSFeed(bakery_feeds.BuildableFeed):
    link = "/latest.xml"
    build_path = "latest.xml"

    def items(self):
        return MockObject.objects.all()


class MockSubjectRSSFeed(bakery_feeds.BuildableFeed):
    link = "/latest.xml"

    def get_object(self, request, obj_id):
        return MockObject.objects.get(pk=obj_id)

    def get_queryset(self):
        return MockObject.objects.all()

    def get_content(self, obj):
        return super().get_content(obj.id)

    def build_path(self, obj):
        return "{}/feed.xml".format(obj.id)

    def items(self, obj):
        return MockObject.objects.none()


# --- Mixins and other helper views ---
class JSONResponseMixin:
    def render_to_response(self, context, **response_kwargs):
        return HttpResponse(
            self.convert_context_to_json(context),
            content_type="application/json",
            **response_kwargs,
        )

    def convert_context_to_json(self, context):
        return json.dumps(context)


class MockJSONView(JSONResponseMixin, bakery_views.BuildableTemplateView):
    build_path = "jsonview.json"

    def get_content(self):
        # Assuming self.request is set up by the test or BuildableTemplateView
        return self.get(self.request).content

    def get_context_data(self, **kwargs):
        return {"hello": "tests"}
