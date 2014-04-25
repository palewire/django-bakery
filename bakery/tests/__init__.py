from __future__ import absolute_import
import os
import six
import django
from .. import views
from django.db import models
from .. import models as bmodels
from django.conf import settings
from django.test import TestCase
from django.core.management import call_command
from django.core.management.base import CommandError


class MockObject(bmodels.BuildableModel):
    detail_views = ['bakery.tests.MockDetailView']
    name = models.CharField(max_length=500)

    def get_absolute_url(self):
        return '/%s/' % self.id


class MockDetailView(views.BuildableDetailView):
    model = MockObject
    template_name = 'detailview.html'


class BakeryTest(TestCase):

    def setUp(self):
        MockObject.objects.create(name=1)
        MockObject.objects.create(name=2)
        MockObject.objects.create(name=3)

    def test_models(self):
        obj = MockObject.objects.all()[0]
        obj.build()
        obj.unbuild()
        bmodels.BuildableModel().get_absolute_url()

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

    def test_404_view(self):
        v = views.Buildable404View()
        v.build_method
        v.build()
        build_path = os.path.join(settings.BUILD_DIR, '404.html')
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
            'Hello tests'
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

    def test_unpublish_cmd(self):
        pass
