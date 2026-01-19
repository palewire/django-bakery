# C:/dev/git_clones/django-bakery/bakery/tests/__init__.py
import json
import logging
import os
import random

# import sys # No longer needed after removing print_to_stderr
from datetime import date
from pathlib import Path

import boto3
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from moto import mock_aws

from bakery import static_views as bakery_original_static_views
from bakery import views as bakery_original_views
from bakery.management.commands import get_s3_client as bakery_get_s3_client

try:
    from django.urls import reverse_lazy
except ImportError:  # Django <2.0
    pass

try:
    from django.urls import path, re_path
except ImportError:  # Django <2.0
    from django.urls import re_path as url


def mock_url_view_func(*args, **kwargs):
    pass


logger = logging.getLogger(__name__)

urlpatterns = [
    re_path(r"^filename\.html$", mock_url_view_func, name="filename"),
    re_path(
        r"^directory/filename\.html$",
        mock_url_view_func,
        name="directory_and_filename",
    ),
    re_path(
        r"^nested/directory/filename\.html$",
        mock_url_view_func,
        name="nested_directory_and_filename",
    ),
]

# Removed print_to_stderr function as it's no longer used.


class BakeryTest(TestCase):
    mock_models_module = None
    test_views = None
    MockObject = None
    AutoMockObject = None
    NoUrlObject = None
    MockDetailView = None
    MockArchiveIndexView = None
    MockArchiveYearView = None
    MockArchiveMonthView = None
    MockArchiveDayView = None
    MockRedirectView = None
    MockRSSFeed = None
    MockSubjectRSSFeed = None
    MockJSONView = None
    NoUrlDetailView = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from . import models as local_test_models_module
        from . import views as local_test_views_module

        cls.mock_models_module = local_test_models_module
        cls.test_views = local_test_views_module

        cls.MockObject = cls.mock_models_module.MockObject
        cls.AutoMockObject = cls.mock_models_module.AutoMockObject
        cls.NoUrlObject = cls.mock_models_module.NoUrlObject
        cls.MockDetailView = cls.test_views.MockDetailView
        cls.NoUrlDetailView = cls.test_views.NoUrlDetailView
        cls.MockArchiveIndexView = cls.test_views.MockArchiveIndexView
        cls.MockArchiveYearView = cls.test_views.MockArchiveYearView
        cls.MockArchiveMonthView = cls.test_views.MockArchiveMonthView
        cls.MockArchiveDayView = cls.test_views.MockArchiveDayView
        cls.MockRedirectView = cls.test_views.MockRedirectView
        cls.MockRSSFeed = cls.test_views.MockRSSFeed
        cls.MockSubjectRSSFeed = cls.test_views.MockSubjectRSSFeed
        cls.MockJSONView = cls.test_views.MockJSONView

    def setUp(self):
        self.factory = RequestFactory()
        if self.MockObject and self.AutoMockObject and self.NoUrlObject:
            for m_class in [self.MockObject, self.AutoMockObject, self.NoUrlObject]:
                for i in range(1, 4):  # Creates objects for 2015, 2014, 2013
                    m_class.objects.create(
                        name=f"{m_class.__name__}_obj_{i}",
                        pub_date=date(2016 - i, 1, 1),
                    )

    def test_models(self):
        """
        A function to test mock models.
        """
        if not self.MockObject or not self.AutoMockObject:
            self.skipTest("Mock models not loaded")
            return

        for m_class in [self.MockObject, self.AutoMockObject]:
            if not m_class.objects.exists():
                self.fail(f"No objects created for {m_class.__name__} in setUp for test_models")

            obj = m_class.objects.all()[0]

            if hasattr(obj, "detail_views") and obj.detail_views:
                from django.urls import get_callable

                for view_str in obj.detail_views:
                    try:
                        view_callable = get_callable(view_str)
                        if isinstance(view_callable, type):
                            view_instance = view_callable()
                            # Further checks on view_instance if necessary
                    except Exception as e:
                        # Handle or log error if necessary for test clarity
                        logger.error(f"Error processing view {view_str} in test_models: {e}")
            obj.build()
            obj.unbuild()
            obj.get_absolute_url()

    def test_template_view_with_explicit_filename(self):
        v = bakery_original_views.BuildableTemplateView(
            template_name="templateview.html",
            build_path="foo.html",
        )
        v.build()
        build_path = os.path.join(settings.BUILD_DIR, "foo.html")
        self.assertTrue(os.path.exists(build_path))
        if os.path.exists(build_path):
            os.remove(build_path)

    @override_settings(ROOT_URLCONF=__name__)
    def test_template_view_with_reversed_explicit_filename(self):
        v = bakery_original_views.BuildableTemplateView(
            template_name="templateview.html",
            build_path=reverse_lazy("filename"),
        )
        v.build()
        build_path = os.path.join(settings.BUILD_DIR, "filename.html")
        self.assertTrue(os.path.exists(build_path))
        if os.path.exists(build_path):
            os.remove(build_path)

    def test_list_view(self):
        v = bakery_original_views.BuildableListView(
            queryset=[1, 2, 3],
            template_name="listview.html",
            build_path="foo.html",
        )
        v.build_queryset()
        build_path = os.path.join(settings.BUILD_DIR, "foo.html")
        self.assertTrue(os.path.exists(build_path))
        if os.path.exists(build_path):
            os.remove(build_path)

        v = bakery_original_views.BuildableListView(
            queryset=[1, 2, 3],
            template_name="listview.html",
            build_path="foo/bar.html",
        )
        v.build_queryset()
        build_path = os.path.join(settings.BUILD_DIR, "foo", "bar.html")
        self.assertTrue(os.path.exists(build_path))
        if os.path.exists(build_path):
            os.remove(build_path)

    def test_detail_view(self):
        if not self.MockObject:
            self.skipTest("MockObject not loaded")
        if not self.MockObject.objects.exists():
            self.fail(
                f"No objects created for {self.MockObject.__name__} in setUp for test_detail_view",
            )

        v = bakery_original_views.BuildableDetailView(
            queryset=self.MockObject.objects.all(),
            template_name="detailview.html",
            # slug_field="this_slug", # Assuming MockObject doesn't have 'this_slug'
            # and relies on get_absolute_url or pk.
        )
        v.build_queryset()
        for o in self.MockObject.objects.all():
            expected_path = os.path.join(
                settings.BUILD_DIR,
                o.get_absolute_url().lstrip("/"),
                "index.html",
            )
            self.assertTrue(os.path.exists(expected_path), f"File not found: {expected_path}")
            v.unbuild_object(o)

    def test_nourl_detail_view(self):
        if not self.NoUrlDetailView:
            self.skipTest("NoUrlDetailView not loaded")
        with self.assertRaises(ImproperlyConfigured):
            self.NoUrlDetailView().build_queryset()

    def test_index_view(self):
        if not self.MockArchiveIndexView:
            self.skipTest("Mock view not loaded")
        v = self.MockArchiveIndexView()
        v.build_queryset()
        build_path = os.path.join(settings.BUILD_DIR, v.build_path)
        self.assertTrue(os.path.exists(build_path), f"File not found: {build_path}")

    def test_year_view(self):
        if not self.MockArchiveYearView:
            self.skipTest("Mock view not loaded")
        v = self.MockArchiveYearView()
        v.build_dated_queryset()
        years_to_check = [
            date(2013, 1, 1),  # Added
            date(2014, 1, 1),
            date(2015, 1, 1),
        ]
        for dt_year_obj in years_to_check:
            v.year = str(dt_year_obj.year)
            expected_path = os.path.join(settings.BUILD_DIR, v.get_build_path())
            self.assertTrue(os.path.exists(expected_path), f"File not found: {expected_path}")

    def test_month_view(self):
        if not self.MockArchiveMonthView:
            self.skipTest("Mock view not loaded")
        v = self.MockArchiveMonthView()
        v.build_dated_queryset()
        dates_to_check = [
            date(2013, 1, 1),  # Added
            date(2014, 1, 1),
            date(2015, 1, 1),
        ]
        for dt_item in dates_to_check:
            v.year = str(dt_item.year)
            v.month = dt_item.strftime(v.get_month_format())
            expected_path = os.path.join(settings.BUILD_DIR, v.get_build_path())
            self.assertTrue(os.path.exists(expected_path), f"File not found: {expected_path}")

    def test_day_view(self):
        if not self.MockArchiveDayView:
            self.skipTest("Mock view not loaded")
        v = self.MockArchiveDayView()
        v.build_dated_queryset()
        dates_to_check = [
            date(2013, 1, 1),  # Added
            date(2014, 1, 1),
            date(2015, 1, 1),
        ]
        for dt_item in dates_to_check:
            v.year = str(dt_item.year)
            v.month = dt_item.strftime(v.get_month_format())
            v.day = dt_item.strftime(v.get_day_format())
            expected_path = os.path.join(settings.BUILD_DIR, v.get_build_path())
            self.assertTrue(os.path.exists(expected_path), f"File not found: {expected_path}")

    def test_redirect_view(self):
        if not self.MockRedirectView:
            self.skipTest("Mock view not loaded")
        v_orig = bakery_original_views.BuildableRedirectView(
            build_path="detail/badurl.html",
            url="/detail/",
        )
        v_orig.build()

        v_mock = self.MockRedirectView()  # Assuming MockRedirectView is configured similarly
        v_mock.build()

        build_path = os.path.join(settings.BUILD_DIR, "detail/badurl.html")
        self.assertTrue(os.path.exists(build_path))

    def test_404_view(self):
        v = bakery_original_views.Buildable404View()
        v.build()
        build_path = os.path.join(settings.BUILD_DIR, "404.html")
        self.assertTrue(os.path.exists(build_path))
        if os.path.exists(build_path):
            os.remove(build_path)

    def test_json_view(self):
        if not self.MockJSONView:
            self.skipTest("Mock view not loaded")
        v = self.MockJSONView()
        v.request = self.factory.get("/")
        v.build()
        build_path = os.path.join(settings.BUILD_DIR, "jsonview.json")
        self.assertTrue(os.path.exists(build_path))
        with open(build_path, "rb") as f:
            content = json.loads(f.read().decode())
        self.assertEqual(content, {"hello": "tests"})
        if os.path.exists(build_path):
            os.remove(build_path)

    def test_rss_feed(self):
        if not self.MockRSSFeed:
            self.skipTest("Mock feed not loaded")
        f = self.MockRSSFeed()
        f.build_method()

        expected_feed_path = os.path.join(settings.BUILD_DIR, f.build_path)
        self.assertTrue(os.path.exists(expected_feed_path), f"File not found: {expected_feed_path}")
        if os.path.exists(expected_feed_path):
            os.remove(expected_feed_path)

    def test_subject_rss_feed(self):
        if not self.MockSubjectRSSFeed or not self.MockObject:
            self.skipTest("Mocks not loaded")
        if not self.MockObject.objects.exists():
            self.fail(
                f"No objects created for {self.MockObject.__name__} in setUp "
                f"for test_subject_rss_feed",
            )

        f = self.MockSubjectRSSFeed()
        f.request = self.factory.get("/")
        build_func = f.build_method
        build_func()

        for obj in self.MockObject.objects.all():
            expected_feed_path = os.path.join(settings.BUILD_DIR, f.build_path(obj))
            self.assertTrue(
                os.path.exists(expected_feed_path),
                f"File not found: {expected_feed_path}",
            )
            if os.path.exists(expected_feed_path):
                os.remove(expected_feed_path)

    def test_build_cmd(self):
        if not hasattr(settings, "BASE_DIR"):
            self.skipTest("BASE_DIR not in settings. Skipping test_build_cmd.")

        test_static_dir = Path(settings.BASE_DIR) / "bakery" / "tests" / "static"
        test_static_dir.mkdir(parents=True, exist_ok=True)
        dummy_static_file = test_static_dir / "foo.bar"
        with open(dummy_static_file, "wb") as f:
            f.write(b"Hello tests\n")

        call_command("build", verbosity=0)  # Reduced verbosity

        foobar_path = os.path.join(settings.BUILD_DIR, "static", "foo.bar")
        self.assertTrue(
            os.path.exists(foobar_path),
            f"{foobar_path} not found. BUILD_DIR: {settings.BUILD_DIR}",
        )
        with open(foobar_path, "rb") as f:
            content = f.read().strip()
        self.assertEqual(content, b"Hello tests")

        if dummy_static_file.exists():
            dummy_static_file.unlink()
        if test_static_dir.exists() and not any(test_static_dir.iterdir()):
            try:
                test_static_dir.rmdir()
            except OSError:
                pass

    def _get_s3_client_tuple_local(self):
        return bakery_get_s3_client()

    def _create_bucket(self):
        s3_client, s3_resource = self._get_s3_client_tuple_local()
        location = {"LocationConstraint": settings.AWS_REGION}
        s3_resource.create_bucket(
            Bucket=settings.AWS_S3_BUCKET_NAME,
            CreateBucketConfiguration=location,
        )

    def _get_bucket_objects(self):
        s3_client, s3_resource = self._get_s3_client_tuple_local()
        return s3_client.list_objects_v2(
            Bucket=settings.AWS_S3_BUCKET_NAME,
        ).get("Contents", [])

    def test_static_views(self):
        if not hasattr(settings, "BASE_DIR"):
            self.skipTest("BASE_DIR not in settings. Skipping test_static_views.")

        test_static_dir = Path(settings.BASE_DIR) / "bakery" / "tests" / "static"
        test_static_dir.mkdir(parents=True, exist_ok=True)
        robots_file = test_static_dir / "robots.txt"
        with open(robots_file, "w") as f:
            f.write("User-agent: *\nDisallow:")

        response = bakery_original_static_views.serve(
            self.factory.get("/static/robots.txt"),
            "robots.txt",
            document_root=str(test_static_dir),
        )
        self.assertEqual(response.status_code, 200)

        if robots_file.exists():
            robots_file.unlink()
        if test_static_dir.exists() and not any(test_static_dir.iterdir()):
            try:
                test_static_dir.rmdir()
            except OSError:
                pass


@override_settings(BAKERY_FILESYSTEM="mem://")
class MemTest(BakeryTest):
    """
    Run all the tests again with a memory backend.
    """

    pass
