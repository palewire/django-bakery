from __future__ import absolute_import
import os
import six
import boto
import json
import random
from moto import mock_s3
from datetime import date
from .. import views, feeds
from django.db import models
from .. import static_views
from django.conf import settings
from .. import models as bmodels
from django.http import HttpResponse
from django.core.management import call_command
from django.test import TestCase, RequestFactory
from django.core.management.base import CommandError
from django.core.exceptions import ImproperlyConfigured
from django.contrib.contenttypes.models import ContentType


class MockObject(bmodels.BuildableModel):
    detail_views = ['bakery.tests.MockDetailView']
    name = models.CharField(max_length=500)
    pub_date = models.DateField()

    def get_absolute_url(self):
        super(MockObject, self).get_absolute_url()  # Just for test coverage
        return '/%s/' % self.id


class NoUrlObject(bmodels.BuildableModel):
    detail_views = ['bakery.tests.MockDetailView']
    name = models.CharField(max_length=500)
    pub_date = models.DateField()


class AutoMockObject(bmodels.AutoPublishingBuildableModel):
    detail_views = ['bakery.tests.MockDetailView']
    name = models.CharField(max_length=500)
    pub_date = models.DateField()
    is_published = models.BooleanField(default=False)

    def get_absolute_url(self):
        return '/%s/' % self.id


class MockDetailView(views.BuildableDetailView):
    model = MockObject
    slug_field = "the_slug"
    template_name = 'detailview.html'


class NoUrlDetailView(views.BuildableDetailView):
    model = NoUrlObject


class MockArchiveIndexView(views.BuildableArchiveIndexView):
    model = MockObject
    date_field = 'pub_date'
    template_name = 'indexview.html'


class MockArchiveYearView(views.BuildableYearArchiveView):
    model = MockObject
    date_field = 'pub_date'
    template_name = 'yearview.html'


class MockArchiveMonthView(views.BuildableMonthArchiveView):
    model = MockObject
    date_field = 'pub_date'
    month_format = "%m"
    template_name = 'monthview.html'


class MockArchiveDayView(views.BuildableDayArchiveView):
    model = MockObject
    date_field = 'pub_date'
    month_format = "%m"
    template_name = 'dayview.html'


class MockRedirectView(views.BuildableRedirectView):
    build_path = "detail/badurl.html"
    url = "/detail/"


class MockRSSFeed(feeds.BuildableFeed):
    link = '/latest.xml'

    def items(self):
        return MockObject.objects.all()


class JSONResponseMixin(object):

    def render_to_response(self, context, **response_kwargs):
        return HttpResponse(
            self.convert_context_to_json(context),
            content_type='application/json',
            **response_kwargs
        )

    def convert_context_to_json(self, context):
        return json.dumps(context)


class MockJSONView(JSONResponseMixin, views.BuildableTemplateView):
    build_path = 'jsonview.json'

    def get_content(self):
        return self.get(self.request).content

    def get_context_data(self, **kwargs):
        return {'hello': 'tests'}


class BakeryTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        for m in [MockObject, AutoMockObject, NoUrlObject]:
            m.objects.create(name=1, pub_date=date(2016, 1, 1))
            m.objects.create(name=2, pub_date=date(2015, 1, 1))
            m.objects.create(name=3, pub_date=date(2014, 1, 1))

    def test_models(self):
        for m in [MockObject, AutoMockObject]:
            obj = m.objects.all()[0]
            obj.build()
            obj.unbuild()
            obj.get_absolute_url()

    def test_template_view(self):
        v = views.BuildableTemplateView(
            template_name='templateview.html',
            build_path='foo.html',
        )
        v.build_method
        v.build()
        build_path = os.path.join(settings.BUILD_DIR, 'foo.html')
        self.assertTrue(os.path.exists(build_path))
        os.remove(build_path)
        v = views.BuildableTemplateView(
            template_name='templateview.html',
            build_path='foo/bar.html',
        )
        v.build_method
        v.build()
        build_path = os.path.join(settings.BUILD_DIR, 'foo', 'bar.html')
        self.assertTrue(os.path.exists(build_path))
        os.remove(build_path)

    def test_list_view(self):
        v = views.BuildableListView(
            queryset=[1, 2, 3],
            template_name='listview.html',
            build_path='foo.html',
        )
        v.build_method
        v.build_queryset()
        build_path = os.path.join(settings.BUILD_DIR, 'foo.html')
        self.assertTrue(os.path.exists(build_path))
        os.remove(build_path)
        v = views.BuildableListView(
            queryset=[1, 2, 3],
            template_name='listview.html',
            build_path='foo/bar.html',
        )
        v.build_method
        v.build_queryset()
        build_path = os.path.join(settings.BUILD_DIR, 'foo', 'bar.html')
        self.assertTrue(os.path.exists(build_path))
        os.remove(build_path)

    def test_detail_view(self):
        v = views.BuildableDetailView(
            queryset=MockObject.objects.all(),
            template_name='detailview.html',
            slug_field="this_slug"
        )
        v.build_method
        v.build_queryset()
        for o in MockObject.objects.all():
            build_path = os.path.join(
                settings.BUILD_DIR,
                o.get_absolute_url()[1:],
                'index.html',
            )
            self.assertTrue(os.path.exists(build_path))
            v.unbuild_object(o)
            self.assertTrue(v.kwargs['slug'] == v.kwargs['this_slug'])

    def test_nourl_detail_view(self):
        with self.assertRaises(ImproperlyConfigured):
            NoUrlDetailView().build_queryset()

    def test_index_view(self):
        v = MockArchiveIndexView()
        v.build_method
        v.build_queryset()
        build_path = os.path.join(settings.BUILD_DIR, v.build_path)
        self.assertTrue(os.path.exists(build_path))

    def test_year_view(self):
        v = MockArchiveYearView()
        v.build_method
        v.build_dated_queryset()
        years = [2014, 2015, 2016]
        for y in years:
            build_path = os.path.join(
                settings.BUILD_DIR,
                'archive',
                '%s' % y,
                'index.html'
            )
            self.assertTrue(os.path.exists(build_path))

    def test_month_view(self):
        v = MockArchiveMonthView()
        v.build_method
        v.build_dated_queryset()
        dates = [('2014', '01'), ('2015', '01'), ('2016', '01')]
        for year, month in dates:
            build_path = os.path.join(
                settings.BUILD_DIR,
                'archive',
                year,
                month,
                'index.html'
            )
            self.assertTrue(os.path.exists(build_path))

    def test_day_view(self):
        v = MockArchiveDayView()
        v.build_method
        v.build_dated_queryset()
        dates = [
            ('2014', '01', '01'),
            ('2015', '01', '01'),
            ('2016', '01', '01')
        ]
        for year, month, day in dates:
            build_path = os.path.join(
                settings.BUILD_DIR,
                'archive',
                year,
                month,
                day,
                'index.html'
            )
            self.assertTrue(os.path.exists(build_path))

    def test_redirect_view(self):
        v = views.BuildableRedirectView(
            build_path="detail/badurl.html",
            url="/detail/"
        )
        v.build_method
        v.build()
        MockRedirectView().build()
        build_path = os.path.join(
            settings.BUILD_DIR,
            "detail/badurl.html"
        )
        self.assertTrue(os.path.exists(build_path))

    def test_404_view(self):
        v = views.Buildable404View()
        v.build_method
        v.build()
        build_path = os.path.join(settings.BUILD_DIR, '404.html')
        self.assertTrue(os.path.exists(build_path))
        os.remove(build_path)

    def test_json_view(self):
        v = MockJSONView()
        v.build()
        build_path = os.path.join(settings.BUILD_DIR, 'jsonview.json')
        self.assertTrue(os.path.exists(build_path))
        self.assertEqual(
            json.loads(open(build_path, 'rb').read().decode()),
            {"hello": "tests"}
        )
        os.remove(build_path)

    def test_rss_feed(self):
        f = MockRSSFeed()
        f.build_method
        f.build_queryset()
        build_path = os.path.join(settings.BUILD_DIR, 'feed.xml')
        self.assertTrue(os.path.exists(build_path))
        os.remove(build_path)

    def test_build_cmd(self):
        call_command("build", **{'skip_media': True, 'verbosity': 3})
        call_command("build", **{'skip_static': True, 'verbosity': 3})
        call_command("build", **{'skip_static': True, 'skip_media': True})
        call_command("build", **{
            'skip_static': True,
            'skip_media': True,
            'verbosity': 3,
        })
        call_command("build", **{
            'skip_static': True,
            'skip_media': True,
            'build_dir': settings.BUILD_DIR,
        })
        call_command("build", 'bakery.tests.MockDetailView')
        foobar_path = os.path.join(
            settings.BUILD_DIR,
            'static',
            'foo.bar'
        )
        self.assertTrue(os.path.exists(foobar_path))
        self.assertEqual(
            open(foobar_path, 'rb').read().strip(),
            six.b('Hello tests')
        )
        robots_path = os.path.join(settings.BUILD_DIR, 'robots.txt')
        self.assertTrue(os.path.exists(robots_path))
        favicon_path = os.path.join(settings.BUILD_DIR, 'favicon.ico')
        self.assertTrue(os.path.exists(favicon_path))
        # If the view you attempt to build does not exist,
        # the build command should throw a CommandError.
        self.assertRaises(
            CommandError,
            call_command,
            'build',
            'FooView',
        )

    def test_unbuild_cmd(self):
        call_command("unbuild")

    def test_gzipped(self):
        with self.settings(BAKERY_GZIP=True):
            six.print_("testing gzipped files")
            self.test_models()
            self.test_template_view()
            self.test_list_view()
            self.test_detail_view()
            self.test_404_view()
            self.test_build_cmd()

    def test_buildserver_cmd(self):
        pass

    def test_publish_cmd(self):
        with mock_s3():
            conn = boto.connect_s3()
            bucket = conn.create_bucket(settings.AWS_BUCKET_NAME)
            call_command("build")
            call_command("publish", no_pooling=True, verbosity=3)
            local_file_list = []
            for (dirpath, dirnames, filenames) in os.walk(
                    settings.BUILD_DIR):
                for fname in filenames:
                    local_key = os.path.join(
                        os.path.relpath(dirpath, settings.BUILD_DIR),
                        fname
                    )
                    if local_key.startswith('./'):
                        local_key = local_key[2:]
                    local_file_list.append(local_key)
            for key in bucket.list():
                self.assertIn(key.name, local_file_list)
            call_command("unbuild")
            os.makedirs(settings.BUILD_DIR)
            call_command("publish", no_pooling=True, verbosity=3)

    def test_unpublish_cmd(self):
        with mock_s3():
            conn = boto.connect_s3()
            bucket = conn.create_bucket(settings.AWS_BUCKET_NAME)
            call_command("build")
            call_command("unpublish", no_pooling=True, verbosity=3)
            self.assertFalse(list(key for key in bucket.list()))

    def test_tasks(self):
        from bakery import tasks
        obj = AutoMockObject.objects.all()[0]
        ct = ContentType.objects.get_for_model(obj)
        tasks.publish_object(ct.id, obj.id)
        tasks.unpublish_object(ct.id, obj.id)
        # Some save overrides tests
        obj = AutoMockObject.objects.all()[0]
        obj.save(publish=False)
        obj.save()
        obj.is_published = True
        obj.save()
        obj.is_published = False
        obj.save()
        obj.delete()

    def test_static_views(self):
        static_views.serve(
            self.factory.get("/static/robots.txt"),
            'robots.txt',
            document_root=os.path.join(os.path.dirname(__file__), 'static')
        )

    def test_cache_control(self):
        with mock_s3():
            # Set random max-age for various content types
            with self.settings(BAKERY_CACHE_CONTROL={
                "application/javascript": random.randint(0, 100000),
                "text/css": random.randint(0, 100000),
                "text/html": random.randint(0, 100000),
            }):
                conn = boto.connect_s3()
                bucket = conn.create_bucket(settings.AWS_BUCKET_NAME)
                call_command("build")
                call_command("publish", no_pooling=True, verbosity=3)
                for key in bucket:
                    key = bucket.get_key(key.name)
                    if key.content_type in settings.BAKERY_CACHE_CONTROL:
                        # key.cache_control returns string
                        # with "max-age=" prefix
                        self.assertIn(
                            str(settings.BAKERY_CACHE_CONTROL.get(
                                key.content_type)),
                            key.cache_control
                        )

    def test_batch_unpublish(self):
        with mock_s3():
            conn = boto.connect_s3()
            bucket = conn.create_bucket(settings.AWS_BUCKET_NAME)
            keys = []
            for i in range(0, 10000):
                k = boto.s3.key.Key(bucket)
                k.key = i
                k.set_contents_from_string('This is test object %s' % i)
                keys.append(k)
            call_command("unpublish", no_pooling=True, verbosity=3)
            self.assertFalse(list(key for key in bucket.list()))
