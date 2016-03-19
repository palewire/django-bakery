from django.contrib import admin
from django.conf.urls import url, include
from date_views.views import (
    MyIndexView,
    MyYearArchiveView,
    MyMonthArchiveView
)
from date_views.models import Article


urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^archive/$', MyIndexView.as_view()),
    url(r'^archive/(?P<year>[0-9]{4})/$', MyYearArchiveView.as_view()),
    url(
        r'^archive/(?P<year>[0-9]{4})/(?P<month>[0-9]+)/$',
        MyMonthArchiveView.as_view(month_format='%m')
    ),
]
