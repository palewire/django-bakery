from django.contrib import admin
from django.conf.urls import url, include
from date_views.views import (
    MyIndexView,
    MyYearArchiveView,
    MyMonthArchiveView,
    MyDayArchiveView
)


urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^archive/$', MyIndexView.as_view()),
    url(r'^archive/(?P<year>[0-9]{4})/$', MyYearArchiveView.as_view()),
    url(
        r'^archive/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/$',
        MyMonthArchiveView.as_view()
    ),
    url(
        r'^archive/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/(?P<day>[0-9]+)/$',
        MyDayArchiveView.as_view(),
    ),
]
