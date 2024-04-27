# Buildable models

## Models that build themselves

If your site pub­lishes numerous pages built from a large data­base, the build-and-pub­lish routine can take
a long time to run. Some­times that’s ac­cept­able, but if you’re peri­od­ic­ally
mak­ing small up­dates to the site it can be frus­trat­ing to wait for the en­tire
data­base to re­build every time there’s a minor edit.

We tackle this prob­lem by hook­ing tar­geted build routines to our Django mod­els.
When an ob­ject is ed­ited, the mod­el is able to re­build only those pages that
ob­ject is con­nec­ted to. We ac­com­plish this with a `BuildableModel` class
you can in­her­it. It works the same as a standard Django model, except that
you are asked define a list of the de­tail views con­nec­ted to each ob­ject.

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

        from django.db im­port mod­els
        from bakery.mod­els im­port Build­ableMod­el


        class My­Mod­el(Build­ableMod­el):
            de­tail_views = ('myapp.views.ExampleDetailView',)
            title = mod­els.Char­Field(max_length=100)
            slug = models.SlugField(max_length=100)
            de­scrip­tion = mod­els.Text­Field()
            is_published = models.BooleanField(default=False)

            def get_absolute_url(self):
                """
                If you are going to publish a detail view for each object,
                one easy way to set the path where it will be built is to
                configure Django's standard get_absolute_url method.
                """
                return '/%s/' % self.slug

            def _build_re­lated(self):
                from myapp import views
                views.MySitem­apView().build_queryset()
                views.MyRSS­Feed().build_queryset()

```

## Models that publish themselves

With a buildable model in place, you can take things a step further with the
`AutoPublishingBuildableModel` so that a up­date pos­ted to the data­base by an entrant
us­ing the [Django ad­min](https://docs.djangoproject.com/en/dev/ref/contrib/admin/)
can set in­to mo­tion a small build that is then synced with your live site on Amazon S3.

At the Los Angeles Times Data Desk, we use that sys­tem to host ap­plic­a­tions
with in-house Django ad­min­is­tra­tion pan­els that, for the entrant, walk and
talk like a live website, but behind the scenes auto­mat­ic­ally fig­ure out how
to serve them­selves on the Web as flat files. That’s how a site like
[graphics.latimes.com](http://graphics.latimes.com) is man­aged.

This is accomplished by handing off the build from the user’s save re­quest in the ad­min to a
job serv­er that does the work in the back­ground. This pre­vents a user who makes a push-but­ton save
in the ad­min from hav­ing to wait for the full process to com­plete be­fore receiving a re­sponse.

This is done by passing off build in­struc­tions to [a Cel­ery job serv­er](http://celery.readthedocs.org/en/latest/django/first-steps-with-django.html).
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

        from django.db im­port mod­els
        from bakery.mod­els im­port AutoPublishingBuildableModel


        class My­Mod­el(AutoPublishingBuildableModel):
            de­tail_views = ('myapp.views.ExampleDetailView',)
            title = mod­els.Char­Field(max_length=100)
            slug = models.SlugField(max_length=100)
            de­scrip­tion = mod­els.Text­Field()
            is_published = models.BooleanField(default=False)

            def get_absolute_url(self):
                """
                If you are going to publish a detail view for each object,
                one easy way to set the path where it will be built is to
                configure Django's standard get_absolute_url method.
                """
                return '/%s/' % self.slug
```
