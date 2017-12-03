from __future__ import unicode_literals
from django.db import models
try:
    from django.core.urlresolvers import reverse
except ImportError:  # Starting with Django 2.0, django.core.urlresolvers does not exist anymore
    from django.urls import reverse


class Article(models.Model):
    """
    A story.
    """
    title = models.CharField(max_length=200)
    pub_date = models.DateField()
    dateline = models.ForeignKey('Dateline', null=True, on_delete=models.CASCADE)

    def get_absolute_url(self):
        return reverse('article-detail', kwargs={'pk': self.pk})


class Dateline(models.Model):
    """
    The location where a story was filed.
    """
    city = models.CharField(max_length=500)
    state = models.CharField(max_length=500)

    city_slug = models.SlugField(max_length=500)
    state_slug = models.SlugField(max_length=500)

    class Meta:
        unique_together = ("city_slug", "state_slug")

    def get_absolute_url(self):
        return reverse('dateline-detail', kwargs={'city_slug': self.city_slug, 'state_slug': self.state_slug})
