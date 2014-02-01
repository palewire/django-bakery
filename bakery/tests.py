import views
from django.test import TestCase


class BakeryTest(TestCase):

    def setUp(self):
        pass

    def test_template_view(self):
        v = views.BuildableTemplateView(
            template_name='foo.html',
            build_path='./foo.html',
        )

    def test_list_view(self):
        v = views.BuildableListView(
            queryset=[1,2,3],
            template_name='foo.html',
            build_path='./foo.html',
        )

    def test_detail_view(self):
        v = views.BuildableDetailView(
            queryset=[1,2,3],
            template_name='foo.html',
            build_path='./foo.html',
        )

