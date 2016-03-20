from date_views.models import Article
from bakery.views import (
    BuildableArchiveIndexView,
    BuildableYearArchiveView,
    BuildableMonthArchiveView,
    BuildableDayArchiveView
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
