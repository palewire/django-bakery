import json
import os
from datetime import date
from pathlib import Path
from unittest.mock import patch

import boto3
import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db import models
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.urls import path, reverse_lazy
from moto import mock_aws

from bakery import feeds, static_views, views
from bakery import models as bmodels
from bakery.management.commands import get_s3_client


def mock_url_view(*args, **kwargs):
    # url objects require a function
    pass


urlpatterns = [
    path("filename.html", mock_url_view, name="filename"),
    path("directory/filename.html", mock_url_view, name="directory_and_filename"),
    path(
        "nested/directory/filename.html",
        mock_url_view,
        name="nested_directory_and_filename",
    ),
]


@pytest.fixture(autouse=True)
def isolated_build_directory(settings, tmp_path):
    settings.BUILD_DIR = str(tmp_path)


class MockObject(bmodels.BuildableModel):
    detail_views = ("bakery.tests.MockDetailView",)
    name = models.CharField(max_length=500)
    pub_date = models.DateField()

    def get_absolute_url(self):
        super().get_absolute_url()  # Just for test coverage
        return f"/{self.id}/"


class NoUrlObject(bmodels.BuildableModel):
    detail_views = ("bakery.tests.MockDetailView",)
    name = models.CharField(max_length=500)
    pub_date = models.DateField()


class AutoMockObject(bmodels.AutoPublishingBuildableModel):
    detail_views = ("bakery.tests.MockDetailView",)
    name = models.CharField(max_length=500)
    pub_date = models.DateField()
    is_published = models.BooleanField(default=False)

    def get_absolute_url(self):
        return f"/{self.id}/"


class MockDetailView(views.BuildableDetailView):
    model = MockObject
    slug_field = "the_slug"
    template_name = "detailview.html"


class NoUrlDetailView(views.BuildableDetailView):
    model = NoUrlObject


class MockArchiveIndexView(views.BuildableArchiveIndexView):
    model = MockObject
    date_field = "pub_date"
    template_name = "indexview.html"


class MockArchiveYearView(views.BuildableYearArchiveView):
    model = MockObject
    date_field = "pub_date"
    template_name = "yearview.html"


class MockArchiveMonthView(views.BuildableMonthArchiveView):
    model = MockObject
    date_field = "pub_date"
    month_format = "%m"
    template_name = "monthview.html"


class MockArchiveDayView(views.BuildableDayArchiveView):
    model = MockObject
    date_field = "pub_date"
    month_format = "%m"
    template_name = "dayview.html"


class MockRedirectView(views.BuildableRedirectView):
    build_path = "detail/badurl.html"
    url = "/detail/"


class MockRSSFeed(feeds.BuildableFeed):
    link = "/latest.xml"

    def items(self):
        return MockObject.objects.all()


class MockSubjectRSSFeed(feeds.BuildableFeed):
    link = "/latest.xml"

    def get_object(self, request, obj_id):
        return MockObject.objects.get(pk=obj_id)

    def get_queryset(self):
        return MockObject.objects.all()

    def get_content(self, obj):
        return super().get_content(obj.id)

    def build_path(self, obj):
        return f"{obj.id}/feed.xml"

    def items(self, obj):
        # Realistically there would be a second model here
        return MockObject.objects.none()


class JSONResponseMixin:
    def render_to_response(self, context, **response_kwargs):
        return HttpResponse(
            self.convert_context_to_json(context),
            content_type="application/json",
            **response_kwargs,
        )

    def convert_context_to_json(self, context):
        return json.dumps(context)


class MockJSONView(JSONResponseMixin, views.BuildableTemplateView):
    build_path = "jsonview.json"

    def get_content(self):
        return self.get(self.request).content

    def get_context_data(self, **kwargs):
        return {"hello": "tests"}


class BakeryTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        for m in [MockObject, AutoMockObject, NoUrlObject]:
            m.objects.create(name=1, pub_date=date(2016, 1, 1))
            m.objects.create(name=2, pub_date=date(2015, 1, 1))
            m.objects.create(name=3, pub_date=date(2014, 1, 1))

    def tearDown(self):
        boto3.DEFAULT_SESSION = None
        super().tearDown()

    def test_models(self):
        for m in [MockObject, AutoMockObject]:
            obj = m.objects.all()[0]
            obj.build()
            obj.unbuild()
            obj.get_absolute_url()

    def test_template_view_with_explicit_filename(self):
        v = views.BuildableTemplateView(
            template_name="templateview.html",
            build_path="foo.html",
        )
        assert v.build_method
        v.build()
        build_path = Path(settings.BUILD_DIR).joinpath("foo.html")
        assert build_path.exists()
        build_path.unlink()

    def test_template_view_with_directory_and_explicit_filename(self):
        v = views.BuildableTemplateView(
            template_name="templateview.html",
            build_path="foo/bar.html",
        )
        assert v.build_method
        v.build()
        build_path = Path(settings.BUILD_DIR).joinpath("foo", "bar.html")
        assert build_path.exists()
        build_path.unlink()

    def test_template_view_with_nested_directory_and_explicit_filename(self):
        v = views.BuildableTemplateView(
            template_name="templateview.html",
            build_path="nested/foo/bar.html",
        )
        assert v.build_method
        v.build()
        build_path = Path(settings.BUILD_DIR).joinpath("nested", "foo", "bar.html")
        assert build_path.exists()
        build_path.unlink()

    @override_settings(ROOT_URLCONF=__name__)
    def test_template_view_with_reversed_explicit_filename(self):
        v = views.BuildableTemplateView(
            template_name="templateview.html",
            build_path=reverse_lazy("filename"),
        )
        assert v.build_method
        v.build()
        build_path = Path(settings.BUILD_DIR).joinpath("filename.html")
        assert build_path.exists()
        build_path.unlink()

    @override_settings(ROOT_URLCONF=__name__)
    def test_template_view_with_reversed_directory_and_explicit_filename(self):
        v = views.BuildableTemplateView(
            template_name="templateview.html",
            build_path=reverse_lazy("directory_and_filename"),
        )
        assert v.build_method
        v.build()
        build_path = Path(settings.BUILD_DIR).joinpath("directory", "filename.html")
        assert build_path.exists()
        build_path.unlink()

    @override_settings(ROOT_URLCONF=__name__)
    def test_template_view_with_reversed_nested_directory_and_explicit_filename(self):
        v = views.BuildableTemplateView(
            template_name="templateview.html",
            build_path=reverse_lazy("nested_directory_and_filename"),
        )
        assert v.build_method
        v.build()
        build_path = Path(settings.BUILD_DIR).joinpath(
            "nested", "directory", "filename.html"
        )
        assert build_path.exists()
        build_path.unlink()

    def test_list_view(self):
        v = views.BuildableListView(
            queryset=[1, 2, 3],
            template_name="listview.html",
            build_path="foo.html",
        )
        assert v.build_method
        v.build_queryset()
        build_path = Path(settings.BUILD_DIR).joinpath("foo.html")
        assert build_path.exists()
        build_path.unlink()
        v = views.BuildableListView(
            queryset=[1, 2, 3],
            template_name="listview.html",
            build_path="foo/bar.html",
        )
        assert v.build_method
        v.build_queryset()
        build_path = Path(settings.BUILD_DIR).joinpath("foo", "bar.html")
        assert build_path.exists()
        build_path.unlink()

    def test_detail_view(self):
        v = views.BuildableDetailView(
            queryset=MockObject.objects.all(),
            template_name="detailview.html",
            slug_field="this_slug",
        )
        assert v.build_method
        v.build_queryset()
        for o in MockObject.objects.all():
            build_path = Path(settings.BUILD_DIR).joinpath(
                o.get_absolute_url().lstrip("/"),
                "index.html",
            )
            assert build_path.exists()
            v.unbuild_object(o)
            assert v.kwargs["slug"] == v.kwargs["this_slug"]

    def test_nourl_detail_view(self):
        with pytest.raises(ImproperlyConfigured):
            NoUrlDetailView().build_queryset()

    def test_index_view(self):
        v = MockArchiveIndexView()
        assert v.build_method
        v.build_queryset()
        build_path = Path(settings.BUILD_DIR).joinpath(v.build_path)
        assert build_path.exists()

    def test_year_view(self):
        v = MockArchiveYearView()
        assert v.build_method
        v.build_dated_queryset()
        years = [2014, 2015, 2016]
        for y in years:
            build_path = Path(settings.BUILD_DIR).joinpath(
                "archive", f"{y}", "index.html"
            )
            assert build_path.exists()

    def test_month_view(self):
        v = MockArchiveMonthView()
        assert v.build_method
        v.build_dated_queryset()
        dates = [("2014", "01"), ("2015", "01"), ("2016", "01")]
        for year, month in dates:
            build_path = Path(settings.BUILD_DIR).joinpath(
                "archive", year, month, "index.html"
            )
            assert build_path.exists()

    def test_day_view(self):
        v = MockArchiveDayView()
        assert v.build_method
        v.build_dated_queryset()
        dates = [("2014", "01", "01"), ("2015", "01", "01"), ("2016", "01", "01")]
        for year, month, day in dates:
            build_path = Path(settings.BUILD_DIR).joinpath(
                "archive", year, month, day, "index.html"
            )
            assert build_path.exists()

    def test_redirect_view(self):
        v = views.BuildableRedirectView(build_path="detail/badurl.html", url="/detail/")
        assert v.build_method
        v.build()
        MockRedirectView().build()
        build_path = Path(settings.BUILD_DIR).joinpath("detail/badurl.html")
        assert build_path.exists()

    def test_404_view(self):
        v = views.Buildable404View()
        assert v.build_method
        v.build()
        build_path = Path(settings.BUILD_DIR).joinpath("404.html")
        assert build_path.exists()
        build_path.unlink()

    def test_json_view(self):
        v = MockJSONView()
        v.build()
        build_path = Path(settings.BUILD_DIR).joinpath("jsonview.json")
        assert build_path.exists()
        assert json.loads(build_path.open("rb").read().decode()) == {"hello": "tests"}
        build_path.unlink()

    def test_rss_feed(self):
        f = MockRSSFeed()
        f.build_method()
        build_path = Path(settings.BUILD_DIR).joinpath("feed.xml")
        assert build_path.exists()
        build_path.unlink()

    def test_subject_rss_feed(self):
        f = MockSubjectRSSFeed()
        f.build_method()
        for obj in MockObject.objects.all():
            build_path = Path(settings.BUILD_DIR).joinpath(str(obj.id), "feed.xml")
            assert build_path.exists()
            build_path.unlink()

    def test_build_cmd(self):
        call_command("build", skip_media=True, verbosity=3)
        call_command("build", skip_static=True, verbosity=3)
        call_command("build", skip_static=True, skip_media=True)
        call_command("build", skip_static=True, skip_media=True, verbosity=3)
        call_command(
            "build", skip_static=True, skip_media=True, build_dir=settings.BUILD_DIR
        )
        call_command("build", "bakery.tests.MockDetailView")
        foobar_path = Path(settings.BUILD_DIR).joinpath("static", "foo.bar")
        assert foobar_path.exists()
        with foobar_path.open("rb") as foobar_file:
            assert foobar_file.read().strip() == b"Hello tests"
        robots_path = Path(settings.BUILD_DIR).joinpath("robots.txt")
        assert robots_path.exists()
        favicon_path = Path(settings.BUILD_DIR).joinpath("favicon.ico")
        assert favicon_path.exists()

    def test_build_pathlib(self):
        with self.settings(BUILD_DIR=Path(settings.BUILD_DIR)):
            call_command("build", verbosity=3)
        with self.settings(STATIC_ROOT=Path(settings.BUILD_DIR) / "_static"):
            call_command("build", verbosity=3)

    def test_unbuild_cmd(self):
        call_command("unbuild")

    def test_gzipped(self):
        with self.settings(BAKERY_GZIP=True):
            self.test_models()
            self.test_template_view_with_explicit_filename()
            self.test_template_view_with_directory_and_explicit_filename()
            self.test_template_view_with_nested_directory_and_explicit_filename()
            self.test_template_view_with_reversed_explicit_filename()
            self.test_template_view_with_reversed_directory_and_explicit_filename()
            self.test_template_view_with_reversed_nested_directory_and_explicit_filename()
            self.test_list_view()
            self.test_detail_view()
            self.test_404_view()
            self.test_build_cmd()

    def test_buildserver_cmd(self):
        pass

    def _create_bucket(self):
        _s3_client, s3_resource = get_s3_client()
        location = {"LocationConstraint": settings.AWS_REGION}
        s3_resource.create_bucket(
            Bucket=settings.AWS_BUCKET_NAME, CreateBucketConfiguration=location
        )

    def _get_bucket_objects(self):
        s3_client, _s3_resource = get_s3_client()
        return s3_client.list_objects_v2(Bucket=settings.AWS_BUCKET_NAME).get(
            "Contents", []
        )

    def test_publish_cmd(self):
        with mock_aws():
            self._create_bucket()
            call_command("build")
            call_command("publish", verbosity=3)
            call_command("unbuild")
            Path(settings.BUILD_DIR).mkdir()
            call_command("publish", verbosity=3)
            call_command("publish", no_delete=True, force=True)
            call_command("publish", aws_bucket_prefix="my-branch")

    def test_unpublish_cmd(self):
        with mock_aws():
            self._create_bucket()
            call_command("build")
            call_command("unpublish", verbosity=3)
            assert not self._get_bucket_objects()

    # def test_tasks(self):
    #     from bakery import tasks
    #     obj = AutoMockObject.objects.all()[0]
    #     ct = ContentType.objects.get_for_model(obj)
    #     tasks.publish_object(ct.id, obj.id)
    #     tasks.unpublish_object(ct.id, obj.id)
    #     # Some save overrides tests
    #     obj = AutoMockObject.objects.all()[0]
    #     obj.save(publish=False)
    #     obj.save()
    #     obj.is_published = True
    #     obj.save()
    #     obj.is_published = False
    #     obj.save()
    #     obj.delete()

    def test_static_views(self):
        static_views.serve(
            self.factory.get("/static/robots.txt"),
            "robots.txt",
            document_root=Path(__file__).parent / "static",
        )

    def test_cache_control(self):
        with mock_aws():
            s3 = boto3.resource("s3", region_name=settings.AWS_REGION)
            with self.settings(
                BAKERY_CACHE_CONTROL={
                    "application/javascript": 3600,
                    "text/css": 7200,
                    "text/html": 10800,
                }
            ):
                self._create_bucket()
                call_command("build")
                call_command("publish", verbosity=3)

                for obj in self._get_bucket_objects():
                    s3_obj = s3.Object(settings.AWS_BUCKET_NAME, obj.get("Key"))

                    if s3_obj.content_type in settings.BAKERY_CACHE_CONTROL:
                        # key.cache_control returns string
                        # with "max-age=" prefix
                        assert (
                            str(settings.BAKERY_CACHE_CONTROL.get(s3_obj.content_type))
                            in s3_obj.cache_control
                        )

    def test_batch_unpublish(self):
        with mock_aws():
            _s3_client, s3_resource = get_s3_client()
            self._create_bucket()
            keys = []
            for i in range(377):
                key = str(i)
                obj = s3_resource.Object(settings.AWS_BUCKET_NAME, key)
                obj.put(Body=f"This is test object {i}")
                keys.append(key)
            call_command("unpublish", verbosity=3)
            assert not self._get_bucket_objects()

    def test_get_s3_client_honors_settings_over_environ(self):
        with (
            patch.dict(
                os.environ,
                {
                    "AWS_ACCESS_KEY_ID": "env_access",
                    "AWS_SECRET_ACCESS_KEY": "env_secret",
                },
            ),
            self.settings(
                AWS_ACCESS_KEY_ID="settings_access",
                AWS_SECRET_ACCESS_KEY="settings_secret",  # noqa: S106
            ),
        ):
            get_s3_client()
            credentials = boto3.DEFAULT_SESSION.get_credentials()
            assert credentials.access_key == "settings_access"
            assert credentials.secret_key == "settings_secret"

    @override_settings()
    def test_get_s3_client_handles_no_settings_gracefully(self):
        with patch.dict(
            os.environ,
            {"AWS_ACCESS_KEY_ID": "env_access", "AWS_SECRET_ACCESS_KEY": "env_secret"},
        ):
            del settings.AWS_ACCESS_KEY_ID
            del settings.AWS_SECRET_ACCESS_KEY
            get_s3_client()

    @override_settings(AWS_S3_ENDPOINT="https://example.com", AWS_S3_HOST="foobar.com")
    def test_aws_s3_endpoint_can_be_set(self):
        s3_client, s3_resource = get_s3_client()
        assert s3_client.meta.endpoint_url == "https://example.com"
        assert s3_resource.meta.client._endpoint.host == "https://example.com"

    @override_settings(AWS_S3_HOST="example.com")
    def test_aws_s3_host_can_be_set(self):
        s3_client, s3_resource = get_s3_client()
        assert s3_client.meta.endpoint_url == "https://example.com"
        assert s3_resource.meta.client._endpoint.host == "https://example.com"

    @override_settings(AWS_S3_HOST="example.com", AWS_S3_USE_SSL=False)
    def test_aws_s3_http_host_can_be_set(self):
        s3_client, s3_resource = get_s3_client()
        assert s3_client.meta.endpoint_url == "http://example.com"
        assert s3_resource.meta.client._endpoint.host == "http://example.com"

    # @mock_s3
    # def test_get_all_objects_in_bucket(self):
    #     s3 = boto3.resource('s3', region_name=settings.AWS_REGION)
    #     self._create_bucket()
    #     keys = []
    #     for i in range(0, 33):
    #         key = str(i)
    #         obj = s3.Object(settings.AWS_BUCKET_NAME, key)
    #         obj.put(Body='This is test object %s' % i)
    #         keys.append(key)
    #     all_objects = get_all_objects_in_bucket(
    #         settings.AWS_BUCKET_NAME,
    #         max_keys=9
    #     )
    #     # Note that this test can't be totally relied on until the
    #     # contributions to moto in
    #     # https://github.com/spulec/moto/pull/814 are installed.
    #     # It works either way though.
    #     self.assertEqual(len(keys), len(all_objects))

    # @mock_s3
    # def test_batch_delete_s3_objects(self):
    #     s3_client, s3_resource = get_s3_client()
    #     self._create_bucket()
    #     keys = []
    #     for i in range(0, 33):
    #         key = str(i)
    #         obj = s3_resource.Object(settings.AWS_BUCKET_NAME, key)
    #         obj.put(Body='This is test object %s' % i)
    #         keys.append(key)

    #     all_objects = self._get_bucket_objects()
    #     all_keys = [o.get('Key') for o in all_objects]
    #     batch_delete_s3_objects(
    #         all_keys,
    #         settings.AWS_BUCKET_NAME,
    #         chunk_size=5
    #     )
    #     self.assertFalse(self._get_bucket_objects())


@override_settings(BAKERY_FILESYSTEM="mem://")
class MemTest(BakeryTest):
    """
    Run all the tests again with a memory backend.
    """
