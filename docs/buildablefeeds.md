# Buildable feeds

You can build a RSS feed in much the same manner as {doc}`buildable class-based views </buildableviews>`.

## BuildableFeed

```{eval-rst}
.. py:class:: BuildableFeed(Feed, BuildableMixin)

    Extends `the base Django Feed class <https://docs.djangoproject.com/en/dev/ref/contrib/syndication/>`_ to be buildable.
    Configure it in the same way you configure that plus our bakery options listed below.

    .. py:attribute:: build_path

        The target location of the flat file in the ``BUILD_DIR``.
        Optional. The default is ``latest.xml``,  would place the flat file
        at the site's root. Defining it as ``foo/latest.xml`` would place
        the flat file inside a subdirectory.

    .. py:attribute:: build_method

        An alias to the ``build_queryset`` method used by the :doc:`management commands </managementcommands>`.

    .. py:method:: build_queryset()

        Writes the rendered template's HTML to a flat file. Only override this if you know what you're doing.

    .. py:method:: get_queryset()

        The ``Feed`` class allows a single feed instance to return different content for requests to different URLs.
        The "subject" for a request is determinted by the object returned from the ``get_object`` method, by default ``None``.
        (See `the Django docs <https://docs.djangoproject.com/en/dev/ref/contrib/syndication/#a-complex-example>` for details.)
        Override this method to provide a collection of "subjects" for which bakery should render the feed.

        As in Django, you can replace certain bakery feed attributes (such as ``build_path``) with methods that accept the subject as an extra "obj" parameter.

    **Example myapp/feeds.py**

    .. code-block:: python

        import os
        from myapp.models import MyModel, MyParentModel
        from bakery.feeds import BuildableFeed


        class ExampleRSSFeed(BuildableFeed):
            link = '/'
            feed_url = '/rss.xml'
            build_path = 'rss.xml'

            def items(self):
                return MyModel.objects.filter(is_published=True)


        class ExampleFeedWithSubject(BuildableFeed):
            def get_object(self, request, obj_id):
                return MyParentModel.objects.get(pk=obj_id)

            def get_queryset(self):
                return MyParentModel.objects.filter(is_published=True)

            def get_content(self, obj):
                return super().get_content(obj.id)

            def link(self, obj):
                return obj.get_absolute_url()

            def feed_url(self, obj):
                return os.path.join(obj.get_absolute_url(), 'rss.xml')

            def build_path(self, obj):
                return self.feed_url(obj)[1:]  # Discard initial slash

            def items(self, obj):
                return MyModel.objects.filter(parent__id=obj.id)
```
