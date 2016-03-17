from django.contrib import admin
from django.conf.urls import url, include
from django.views.generic.dates import ArchiveIndexView
from date_views.models import Article


urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^archive/$',
        ArchiveIndexView.as_view(model=Article, date_field="pub_date"),
        name="article_archive"),
]
