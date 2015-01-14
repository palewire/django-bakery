from __future__ import absolute_import
import os
import six
import json
import django
import boto
from boto.s3.key import Key
from moto import mock_s3
from .. import views, feeds
from django.db import models
from .. import models as bmodels
from django.conf import settings
from django.test import TestCase
from django.http import HttpResponse
from django.core.management import call_command
from django.core.management.base import CommandError
from django.contrib.contenttypes.models import ContentType

try:
    from mock import patch
except ImportError:
    from unittest.mock import patch


class MockObject(bmodels.BuildableModel):
    detail_views = ['bakery.tests.MockDetailView']
    name = models.CharField(max_length=500)

    def get_absolute_url(self):
        super(MockObject, self).get_absolute_url()  # Just for test coverage
        return '/%s/' % self.id


class AutoMockObject(bmodels.AutoPublishingBuildableModel):
    detail_views = ['bakery.tests.MockDetailView']
    name = models.CharField(max_length=500)
    is_published = models.BooleanField(default=False)

    def get_absolute_url(self):
        return '/%s/' % self.id


class MockDetailView(views.BuildableDetailView):
    model = MockObject
    template_name = 'detailview.html'


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
        for m in [MockObject, AutoMockObject]:
            m.objects.create(name=1)
            m.objects.create(name=2)
            m.objects.create(name=3)

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
        if django.VERSION >= (1, 5):
            self.assertRaises(
                CommandError,
                call_command,
                'build',
                'FooView',
            )

    def test_unbuild_cmd(self):
        call_command("unbuild")

    def test_gzipped(self):
        if django.VERSION >= (1, 4):
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
        pass

    @mock_s3
    def test_publish_cmd_keep_files(self):
        """
        Test that running the publish management command with the
        --keep-files option does not delete remote files that
        don't exist in the build directory
        """
        aws_bucket_name = 'fake.s3.example.com'

        # Since we're mocking S3, we need to create the mock bucket
        conn = boto.connect_s3()
        bucket = conn.create_bucket(aws_bucket_name)

        # Create an item in S3 that isn't in our build directory
        contents = 'This is a file not in the Django Bakery build'
        key = 'not_in_build/test.html'
        k = Key(bucket)
        k.key = key
        k.set_contents_from_string(contents)

        # Build our mock site via the build management command
        call_command("build", 'bakery.tests.MockDetailView')

        # HACK: Running the publish command causes this exception to be raised:
        # S3DataError: BotoClientError: ETag from S3 did not match computed 
        # MD5.
        # I suspect, but haven't confirmed that this is due to the combination
        # of mocking S3 and threading.  We don't really care about that part
        # of the code, so just mock the offending method
        with patch.object(Key, 'should_retry', return_value=True):
            # Publish the built site
            cmd_kwargs = {
                'keep_files': True,
                'aws_bucket_name': aws_bucket_name,
            }
            call_command('publish', **cmd_kwargs)

            # The key we created should still be in the bucket after publishing
            k = bucket.get_key(key)
            self.assertEqual(k.get_contents_as_string(), contents)

    def test_unpublish_cmd(self):
        pass

    def test_tasks(self):
        from bakery import tasks
        obj = AutoMockObject.objects.all()[0]
        ct = ContentType.objects.get_for_model(obj)
        tasks.publish_object(ct.id, obj.id)
        tasks.unpublish_object(ct.id, obj.id)
        # Some save overrides tests
        obj = AutoMockObject.objects.all()[0]
        obj.save(publish=False)
        # obj.is_published = True
        # obj.save()
        obj.delete(unpublish=False)
