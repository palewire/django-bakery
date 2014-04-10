Buildable models
================

If your site pub­lishes a large data­base, the build-and-pub­lish routine can take a long time to run. Some­times that’s ac­cept­able, but if you’re peri­od­ic­ally mak­ing small up­dates to the site it can be frus­trat­ing to wait for the en­tire data­base to re­build every time there’s a minor edit.

We tackle this prob­lem by hook­ing tar­geted build routines to our Django mod­els. When an ob­ject is ed­ited, the mod­el is able to re­build only those pages that ob­ject is con­nec­ted to. We ac­com­plish this with a ``BuildableModel`` class you can in­her­it. It works the same as a standard Django model, except that you are asked define a list of the de­tail views con­nec­ted to each ob­ject.

BuildableModel
--------------

.. class:: BuildableModel

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


        class My­Mod­el(Build­ableMod­el)
            de­tail_views = ('myapp.views.ExampleDetailView',)
            title = mod­els.Char­Field(max_length=100)
            de­scrip­tion = mod­els.Text­Field()
            is_published = models.BooleanField(default=False)

            def _build_re­lated(self):
                from myapp import views
                views.MySitem­apView().build_queryset()
                views.MyRSS­Feed().build_queryset()

Celery task-queue integration
-----------------------------

With a buildable model in place, a up­date pos­ted to the data­base by an entrant us­ing the `Django ad­min <https://docs.djangoproject.com/en/dev/ref/contrib/admin/>`_ can set in­to mo­tion a small build that is then synced with your live site on Amazon S3. We use that sys­tem to host ap­plic­a­tions with in-house Django ad­min­is­tra­tion pan­els that, for the entrant, walk and talk like a live data­base, but behind the scenes auto­mat­ic­ally fig­ure out how to serve them­selves on the Web as flat files. That’s how a site like `graphics.latimes.com <http://graphics.latimes.com>`_ is man­aged.

This is accomplished by handing off the build from the user’s save re­quest in the ad­min to a job serv­er that does the work in the back­ground. This pre­vents a push-but­ton save in the ad­min from hav­ing to wait for the en­tire build to com­plete be­fore re­turn­ing a re­sponse. Here is the save over­ride that as­sesses wheth­er the pub­lic­a­tion status of an ob­ject has changed, and then passes off build in­struc­tions to `a Cel­ery job serv­er <http://celery.readthedocs.org/en/latest/django/first-steps-with-django.html>`_.

The key is figuring out what build or unbuild actions to trigger in `an override of the Django model's default save method <https://docs.djangoproject.com/en/dev/topics/db/models/#overriding-predefined-model-methods>`_. 

**example myapp/models.py**

.. code-block:: django

    from myapp import tasks
    from django.db im­port mod­els
    from django.db import transaction
    from bakery.mod­els im­port Build­ableMod­el


    class My­Mod­el(Build­ableMod­el)
        de­tail_views = ('myapp.views.ExampleDetailView',)
        title = mod­els.Char­Field(max_length=100)
        de­scrip­tion = mod­els.Text­Field()
        is_published = models.BooleanField(default=False)

        def _build_re­lated(self):
            from myapp import views
            views.MySitem­apView().build_queryset()
            views.MyRSS­Feed().build_queryset()

        @transaction.atomic
        def save(self, *args, **kwargs):
            """
            A custom save that builds or unbuilds when necessary.
            """
            # if obj.save(build=False) has been passed, we skip everything.
            if not kwargs.pop('build', True):
                super(My­Mod­el, self).save(*args, **kwargs)
            # Otherwise, for the standard obj.save(), here we go...
            else:
                # First figure out if the record is an addition, or an edit of
                # a preexisting record.
                try:
                    preexisting = My­Mod­el.objects.get(id=self.id)
                except My­Mod­el.DoesNotExist:
                    preexisting = None
                # If this is an addition...
                if not preexisting:
                    # We will publish if that's the boolean
                    if self.is_published:
                        action = 'publish'
                    # Otherwise we will do nothing do nothing
                    else:
                        action = None
                # If this is an edit...
                else:
                    # If it's being unpublished...
                    if not self.is_published and preexisting.is_published:
                        action = 'unpublish'
                    # If it's being published...
                    elif self.is_published:
                        action = 'publish'
                    # If it's remaining unpublished...
                    else:
                        action = None
                # Now, no matter what, save it normally
                super(My­Mod­el, self).save(*args, **kwargs)
                # Finally, depending on the action, fire off a task
                if action == 'publish':
                    tasks.publish.delay(self)
                elif action == 'unpublish':
                    tasks.unpublish.delay(self)

The tasks don’t have to be com­plic­ated. Ours are as simple as this.

**example myapp/tasks.py**

.. code-block:: python

    im­port sys
    im­port log­ging
    from celery.task import task
    from django.conf im­port set­tings
    from django.core im­port man­age­ment
    log­ger = log­ging.get­Log­ger(__name__)


    @task()
    def publish(obj):
        """
        Build all the pages and then sync with S3.
        """
        try:
            # Here the object is built
            obj.build()
            # And if the set­tings al­low pub­lic­a­tion from this en­vir­on­ment...
            if settings.PUBLISH:
                # ... the pub­lish com­mand is called to sync with S3.
                management.call_command("publish")
        except Exception, exc:
            logger.error(
                "Task Error: publish",
                exc_info=sys.exc_info(),
                extra={
                    'status_code': 500,
                    'request': None
                }
            )


    @task()
    def unpublish(obj):
        """
        Unbuild all the pages and then sync with S3.
        """
        try:
            obj.unbuild()
            if settings.PUBLISH:
                management.call_command("publish")
        except Exception, exc:
            logger.error(
                "Task Error: unpublish",
                exc_info=sys.exc_info(),
                extra={
                    'status_code': 500,
                    'request': None
                }
            )
