from date_views.models import Article, Dateline
from bakery.views import (
    BuildableArchiveIndexView,
    BuildableYearArchiveView,
    BuildableMonthArchiveView,
    BuildableDayArchiveView,
    BuildableDetailView,
)


class MyIndexView(BuildableArchiveIndexView):
    model = Article
    date_field = 'pub_date'
    #allow_future = True
    #paginate_by = 2


class MyYearArchiveView(BuildableYearArchiveView):
    queryset = Article.objects.all()
    date_field = "pub_date"
    make_object_list = True
    #year_format = "%y"
    #allow_future = True


class MyMonthArchiveView(BuildableMonthArchiveView):
    queryset = Article.objects.all()
    date_field = "pub_date"
    month_format = "%m"
    #allow_future = True


class MyDayArchiveView(BuildableDayArchiveView):
    queryset = Article.objects.all()
    date_field = "pub_date"
    month_format = "%m"
    #allow_future = True


class MyDetailView(BuildableDetailView):
    queryset = Dateline.objects.all()

    def set_kwargs(self, obj):
        self.kwargs = {
            'state_slug': obj.state_slug,
            'city_slug': obj.city_slug,
        }

    def get_object(self, queryset=None):
        return self.queryset.get(
            state_slug=self.kwargs['state_slug'],
            city_slug=self.kwargs['city_slug']
        )
