from django.contrib import admin
from .models import Article, Dateline


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    pass


@admin.register(Dateline)
class DatelineAdmin(admin.ModelAdmin):
    pass
