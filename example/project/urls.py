from django.conf.urls import url
from django.views.generic.dates import ArchiveIndexView
from date_views.models import Article


urlpatterns = [
    url(r'^archive/$',
        ArchiveIndexView.as_view(model=Article, date_field="pub_date"),
        name="article_archive"),
]
