from django.contrib import admin
from django.conf.urls import url, include
from date_views.views import MyIndexView
from date_views.models import Article


urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^archive/$', MyIndexView.as_view()),
]
