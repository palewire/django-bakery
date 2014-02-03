from __future__ import absolute_import
import os
import tempfile
from .. import views
from django.db import models
from django.test import TestCase
from django.test.utils import override_settings

TEST_SETTINGS = {
    'TEMPLATE_DIRS': (
        '%s/templates' % os.path.abspath(os.path.dirname(__file__)),
    ),
    'BUILD_DIR': tempfile.mkdtemp(),
}


class MockObject(models.Model):
    name = models.CharField(max_length=500)

    def get_absolute_url(self):
        return '/%s/' % self.id


@override_settings(**TEST_SETTINGS)
class BakeryTest(TestCase):

    def setUp(self):
        MockObject.objects.create(name=1)
        MockObject.objects.create(name=2)
        MockObject.objects.create(name=3)

    def test_template_view(self):
        v = views.BuildableTemplateView(
            template_name='templateview.html',
            build_path='foo.html',
        )
        v.build_method
        v.build()
        build_path = os.path.join(TEST_SETTINGS['BUILD_DIR'], 'foo.html')
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
        build_path = os.path.join(TEST_SETTINGS['BUILD_DIR'], 'foo.html')
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
                TEST_SETTINGS['BUILD_DIR'],
                o.get_absolute_url()[1:],
                'index.html',
            )
            self.assertTrue(os.path.exists(build_path))
            v.unbuild_object(o)
