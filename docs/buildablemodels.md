# Buildable models

## Models that build themselves

If your site publishes numerous pages built from a large database, the build-and-publish routine can take
a long time to run. Sometimes that’s acceptable, but if you’re periodically
making small updates to the site it can be frustrating to wait for the entire
database to rebuild every time there’s a minor edit.

We tackle this problem by hooking targeted build routines to our Django models.
When an object is edited, the model is able to rebuild only those pages that
object is connected to. We accomplish this with a `BuildableModel` class
you can inherit. It works the same as a standard Django model, except that
you are asked define a list of the detail views connected to each object.

### BuildableModel

```{eval-rst}
.. class:: BuildableModel(models.Model)

    An abstract base model that creates an object that can builds out its own detail pages.

    .. attribute:: detail_views

        An iterable containing paths to the views that are built using the object, which should inherit from :doc:`buildable class-based views </buildableviews>`.

    .. method:: build()

        Iterates through the views pointed to by ``detail_views``, running
        each view's ``build_object`` method with ``self``. Then calls ``_build_extra()``
        and ``_build_related()``.

    .. method:: unbuild()

        Iterates through the views pointed to by ``detail_views``, running
        each view's ``unbuild_object`` method with ``self``. Then calls ``_unbuild_extra()``
        and ``_build_related()``.

    .. method:: _build_extra()

        A place to include code that will build extra content related to the object
        that is not rendered by the ``detail_views``, such a related image.
        Empty by default.

    .. method:: _build_related()

        A place to include code that will build related content, such as an RSS feed,
        that does not require passing in the object to a view. Empty by default.

    .. method:: _unbuild_extra()

        A place to include code that will remove extra content related to the object
        that is not rendered by the ``detail_views``, like deleting a related image.
        Empty by default.

    .. code-block:: django

        from django.db import models
        from bakery.models import BuildableModel


        class MyModel(BuildableModel):
            detail_views = ('myapp.views.ExampleDetailView',)
            title = models.CharField(max_length=100)
            slug = models.SlugField(max_length=100)
            description = models.TextField()
            is_published = models.BooleanField(default=False)

            def get_absolute_url(self):
                """
                If you are going to publish a detail view for each object,
                one easy way to set the path where it will be built is to
                configure Django's standard get_absolute_url method.
                """
                return '/%s/' % self.slug

            def _build_related(self):
                from myapp import views
                views.MySitemapView().build_queryset()
                views.MyRSSFeed().build_queryset()

```

## Models that publish themselves

With a buildable model in place, you can take things a step further with the
`AutoPublishingBuildableModel` so that a update posted to the database by an entrant
using the [Django admin](https://docs.djangoproject.com/en/dev/ref/contrib/admin/)
can set into motion a small build that is then synced with your live site on Amazon S3.

At the Los Angeles Times Data Desk, we use that system to host applications
with in-house Django administration panels that, for the entrant, walk and
talk like a live website, but behind the scenes automatically figure out how
to serve themselves on the Web as flat files. That’s how a site like
[graphics.latimes.com](http://graphics.latimes.com) is managed.

This is accomplished by handing off the build from the user’s save request in the admin to a
job server that does the work in the background. This prevents a user who makes a push-button save
in the admin from having to wait for the full process to complete before receiving a response.

This is done by passing off build instructions to [a Celery job server](http://celery.readthedocs.org/en/latest/django/first-steps-with-django.html).
**You need to install Celery and have it fully configured before this model will work.**

### AutoPublishingBuildableModel

```{eval-rst}
.. class:: AutoPublishingBuildableModel(BuildableModel)

    Integrates with Celery tasks to automatically publish or unpublish
    objects when they are saved.

    This is done using an override on the save method that inspects
    if the object ought to be published, republished or unpublished.

    Requires an indicator of whether the object should been
    published or unpublished. By default it looks to a BooleanField
    called ``is_published`` for the answer, but other methods could
    be employed by overriding the ``get_publication_status`` method.

    .. attribute:: publication_status_field

        The name of the field that this model will inspect to determine
        the object's publication status. By default it is ``is_published``.

    .. method:: get_publication_status()

        Returns a boolean (True or False) indicating whether the object
        is "live" and ought to be published or not.

        Used to determine whether the save method should seek to publish,
        republish or unpublish the object when it is saved.

        By default, it looks for a BooleanField with the name defined in
        the model's ``publication_status_field``.

        If your model uses a list of strings or other more complex
        means to indicate publication status you need to override this method
        and have it negotiate your object to return either True or False.

    .. method:: save(publish=True)

        A custom save that uses Celery tasks to publish or unpublish the
        object where appropriate.

        Save with keyword argument obj.save(publish=False) to skip the process.

    .. method:: delete(unpublish=True)

        Triggers a task that will unpublish the object after it is deleted.

        Save with keyword argument obj.delete(unpublish=False) to skip it.

    .. code-block:: django

        from django.db import models
        from bakery.models import AutoPublishingBuildableModel


        class MyModel(AutoPublishingBuildableModel):
            detail_views = ('myapp.views.ExampleDetailView',)
            title = models.CharField(max_length=100)
            slug = models.SlugField(max_length=100)
            description = models.TextField()
            is_published = models.BooleanField(default=False)

            def get_absolute_url(self):
                """
                If you are going to publish a detail view for each object,
                one easy way to set the path where it will be built is to
                configure Django's standard get_absolute_url method.
                """
                return '/%s/' % self.slug
```
