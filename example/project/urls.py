from django.contrib import admin
from django.urls import re_path, include
from date_views.views import (
    MyIndexView,
    MyYearArchiveView,
    MyMonthArchiveView,
    MyDayArchiveView,
    MyDetailView
)


urlpatterns = [
    # url(r'^admin/', include(admin.site.urls)),
    re_path(
        r'^dateline/(?P<state_slug>[-\w]+)/(?P<city_slug>[-\w]+)/$',
        MyDetailView.as_view(),
        name="dateline-detail"
    ),
    re_path(r'^archive/$', MyIndexView.as_view()),
    re_path(r'^archive/(?P<year>[0-9]{4})/$', MyYearArchiveView.as_view()),
    re_path(
        r'^archive/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/$',
        MyMonthArchiveView.as_view()
    ),
    re_path(
        r'^archive/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/(?P<day>[0-9]+)/$',
        MyDayArchiveView.as_view(),
    ),
]
