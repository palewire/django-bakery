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

            def _build_re­lated(self):
                from myapp import views
                views.MySitem­apView().build_queryset()
                views.MyRSS­Feed().build_queryset()

