Buildable feeds
===============

You can build a RSS feed in much the same manner as :doc:`buildable class-based views </buildableviews>`.

BuildableFeed
-------------

.. py:class:: BuildableFeed(Feed, BuildableMixin)

    Extends `the base Django Feed class <https://docs.djangoproject.com/en/dev/ref/contrib/syndication/>`_ to be buildable.
    Configure it in the same way you configure that plus our bakery options listed below.

    .. py:attribute:: build_path

        The target location of the flat file in the ``BUILD_DIR``.
        Optional. The default is ``latest.xml``,  would place the flat file
        at the site's root. Defining it as ``foo/latest.xml`` would place
        the flat file inside a subdirectory.

    .. py:attribute:: build_method

        An alias to the ``build_queryset`` method used by the :doc:`management commands </managementcommands>`

    .. py:method:: build_queryset()

        Writes the rendered template's HTML to a flat file. Only override this if you know what you're doing.

    **Example myapp/feeds.py**

    .. code-block:: python

        from myapp.models import MyModel
        from bakery.feeds import BuildableFeed


        class ExampleRSSFeed(BuildableFeed):
            link = 'http://www.mysite.com/rss.xml'
            build_path = 'rss.xml'

            def items(self):
                return MyModel.objects.filter(is_published=True)
