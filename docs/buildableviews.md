# Buildable views

Django's [class-based views](https://docs.djangoproject.com/en/dev/topics/class-based-views/)  are used to render HTML pages to flat files. Putting all the pieces together is a little tricky at first, particularly if you haven't studied [the Django source code](https://github.com/django/django/tree/master/django/views/generic) or lack experience [working with Python classes](http://www.diveintopython.net/object_oriented_framework/defining_classes.html) in general. But if you figure it out, we think it's worth the trouble.

## BuildableTemplateView

```{eval-rst}
.. py:class:: BuildableTemplateView(TemplateView, BuildableMixin)

    Renders and builds a simple template as a flat file. Extended from Django's
    generic `TemplateView <https://docs.djangoproject.com/en/dev/ref/class-based-views/base/#django.views.generic.base.TemplateView>`_.
    The base class has a number of options not documented here you should consult.

    .. py:attribute:: build_path

        The target location of the built file in the ``BUILD_DIR``.
        ``index.html`` would place it at the built site's root.
        ``foo/index.html`` would place it inside a subdirectory. Required.

    .. py:attribute:: template_name

        The name of the template you would like Django to render. Required.

    .. py:method:: build()

        Writes the rendered template's HTML to a flat file. Only override this if you know what you're doing.

    .. py:attribute:: build_method

        An alias to the ``build`` method used by the :doc:`management commands </managementcommands>`

    **Example myapp/views.py**

    .. code-block:: python

        from bakery.views import BuildableTemplateView

        class ExampleTemplateView(BuildableTemplateView):
            build_path = 'examples/index.html'
            template_name = 'examples.html'

```

## BuildableListView

```{eval-rst}
.. class:: BuildableListView(ListView, BuildableMixin)

    Render and builds a page about a list of objects. Extended from Django's
    generic `ListView <https://docs.djangoproject.com/en/dev/ref/class-based-views/generic-display/#django.views.generic.list.ListView>`_.
    The base class has a number of options not documented here you should consult.

    .. attribute:: model

        A Django database model where the list of objects can be drawn
        with a ``Model.objects.all()`` query. Optional. If you want to provide
        a more specific list, define the ``queryset`` attribute instead.

    .. attribute:: queryset

        The list of objects that will be provided to the template. Can be
        any iterable of items, not just a Django queryset. Optional, but
        if this attribute is not defined the ``model`` attribute must be
        defined.

    .. attribute:: build_path

        The target location of the flat file in the ``BUILD_DIR``.
        Optional. The default is ``index.html``,  would place the flat file
        at the site's root. Defining it as ``foo/index.html`` would place
        the flat file inside a subdirectory.

    .. attribute:: template_name

        The template you would like Django to render. You need
        to override this if you don't want to rely on the Django ``ListView``
        defaults.

    .. py:attribute:: build_method

        An alias to the ``build_queryset`` method used by the :doc:`management commands </managementcommands>`

    .. py:method:: build_queryset()

        Writes the rendered template's HTML to a flat file. Only override this if you know what you're doing.

    **Example myapp/views.py**

    .. code-block:: python

        from myapp.models import MyModel
        from bakery.views import BuildableListView


        class ExampleListView(BuildableListView):
            model = MyModel
            template_name = 'mymodel_list.html'


        class DifferentExampleListView(BuildableListView):
            build_path = 'mymodel/index.html'
            queryset = MyModel.objects.filter(is_published=True)
            template_name = 'mymodel_list.html'
```

(buildable-detail-view)=

## BuildableDetailView

```{eval-rst}
.. class:: BuildableDetailView(DetailView, BuildableMixin)

    Render and build a "detail" page about an object or a series of pages
    about a list of objects. Extended from Django's generic `DetailView <https://docs.djangoproject.com/en/dev/ref/class-based-views/generic-display/#detailview>`_.
    The base class has a number of options not documented here you should consult.

    .. attribute:: model

        A Django database model where the list of objects can be drawn
        with a ``Model.objects.all()`` query. Optional. If you want to provide
        a more specific list, define the ``queryset`` attribute instead.

    .. attribute:: queryset

        The Django model queryset objects are to be looked up from. Optional, but
        if this attribute is not defined the ``model`` attribute must be
        defined.

    .. attribute:: template_name

        The name of the template you would like Django to render. You need
        to override this if you don't want to rely on the default, which is
        ``os.path.join(settings.BUILD_DIR, obj.get_absolute_url(), 'index.html')``.

    .. method:: get_build_path(obj)

        Used to determine where to build the detail page. Override this if you
        would like your detail page at a different location. By default it
        will be built at ``os.path.join(obj.get_url(), "index.html"``.

    .. method:: get_html(obj)

        How to render the output for the provided object's page. If you choose to render
        using something other than a Django template, like HttpResponse for
        instance, you will want to override this. By default it uses the template
        object's default ``render`` method.

    .. _get_url
    .. method:: get_url(obj)

        Returns the build directory, and therefore the URL, where the provided
        object's flat file should be placed. By default it is ``obj.get_absolute_url()``,
        so simplify defining that on your model is enough.

    .. py:attribute:: build_method

        An alias to the ``build_queryset`` method used by the :doc:`management commands </managementcommands>`

    .. py:method:: build_object(obj)

        Writes the rendered HTML for the template and the provided object to the build directory.

    .. py:method:: build_queryset()

        Writes the rendered template's HTML for each object in the ``queryset`` or ``model`` to a flat file. Only override this if you know what you're doing.

    .. py:method:: unbuild_object(obj)

        Deletes the directory where the provided object's flat files are stored.

    **Example myapp/models.py**

    .. code-block:: python

        from django.db im­port mod­els
        from bakery.mod­els im­port Build­ableMod­el


        class My­Mod­el(Build­ableMod­el):
            de­tail_views = ('myapp.views.ExampleDetailView',)
            title = mod­els.Char­Field(max_length=100)
            slug = models.SlugField(max_length=100)

            def get_absolute_url(self):
                """
                If you are going to publish a detail view for each object,
                one easy way to set the path where it will be built is to
                configure Django's standard get_absolute_url method.
                """
                return '/%s/' % self.slug

    **Example myapp/views.py**

    .. code-block:: python

        from myapp.models import MyModel
        from bakery.views import BuildableDetailView


        class ExampleDetailView(BuildableDetailView):
            queryset = MyModel.objects.filter(is_published=True)
            template_name = 'mymodel_detail.html'

```

## BuildableArchiveIndexView

```{eval-rst}
.. class:: BuildableArchiveIndexView(ArchiveIndexView, BuildableMixin)

    Renders and builds a top-level index page showing the “latest” objects,
    by date. Extended from Django's generic `ArchiveIndexView <https://docs.djangoproject.com/en/1.9/ref/class-based-views/generic-date-based/#archiveindexview>`_.
    The base class has a number of options not documented here you should consult.

    .. attribute:: model

        A Django database model where the list of objects can be drawn
        with a ``Model.objects.all()`` query. Optional. If you want to provide
        a more specific list, define the ``queryset`` attribute instead.

    .. attribute:: queryset

        The list of objects that will be provided to the template. Can be
        any iterable of items, not just a Django queryset. Optional, but
        if this attribute is not defined the ``model`` attribute must be
        defined.

    .. attribute:: build_path

        The target location of the flat file in the ``BUILD_DIR``.
        Optional. The default is ``archive/index.html``,  would place the flat file
        at the '/archive/' URL.

    .. attribute:: template_name

        The template you would like Django to render. You need
        to override this if you don't want to rely on the Django default,
        which is ``<model_name_lowercase>_archive.html``.

    .. py:attribute:: build_method

        An alias to the ``build_queryset`` method used by the :doc:`management commands </managementcommands>`

    .. py:method:: build_queryset()

        Writes the rendered template's HTML to a flat file. Only override this if you know what you're doing.

    **Example myapp/views.py**

    .. code-block:: python

        from myapp.models import MyModel
        from bakery.views import BuildableArchiveIndexView


        class ExampleArchiveIndexView(BuildableArchiveIndexView):
            model = MyModel
            date_field = "pub_date"


        class DifferentExampleArchiveIndexView(BuildableArchiveIndexView):
            build_path = 'my-archive-directory/index.html'
            queryset = MyModel.objects.filter(is_published=True)
            date_field = "pub_date"
            template_name = 'mymodel_list.html'

```

## BuildableYearArchiveView

```{eval-rst}
.. class:: BuildableYearArchiveView(YearArchiveView, BuildableMixin)

    Renders and builds a yearly archive showing all available months
    (and, if you'd like, objects) in a given year. Extended from Django's generic `YearArchiveView <https://docs.djangoproject.com/en/1.9/ref/class-based-views/generic-date-based/#yeararchiveview>`_.
    The base class has a number of options not documented here you should consult.

    .. attribute:: model

        A Django database model where the list of objects can be drawn
        with a ``Model.objects.all()`` query. Optional. If you want to provide
        a more specific list, define the ``queryset`` attribute instead.

    .. attribute:: queryset

        The list of objects that will be provided to the template. Can be
        any iterable of items, not just a Django queryset. Optional, but
        if this attribute is not defined the ``model`` attribute must be
        defined.

    .. attribute:: template_name

        The template you would like Django to render. You need
        to override this if you don't want to rely on the Django default,
        which is ``<model_name_lowercase>_archive_year.html``.

    .. method:: get_build_path()

        Used to determine where to build the detail page. Override this if you
        would like your detail page at a different location. By default it
        will be built at ``os.path.join(obj.get_url(), "index.html"``.

    .. method:: get_url()

        The URL at which the detail page should appear. By default it is /archive/ + the year in
        the generic view's ``year_format`` attribute. An example would be /archive/2016/

    .. py:attribute:: build_method

        An alias to the ``build_dated_queryset`` method used by the :doc:`management commands </managementcommands>`

    .. py:method:: build_dated_queryset()

        Writes the rendered HTML for all publishable dates to the build directory.

    .. py:method:: build_year(dt)

        Writes the rendered HTML for the provided year to the build directory.

    .. py:method:: unbuild_year(dt)

        Deletes the directory where the provided year's flat files are stored.

    **Example myapp/views.py**

    .. code-block:: python

        from myapp.models import MyModel
        from bakery.views import BuildableYearArchiveView


        class ExampleArchiveYearView(BuildableYearArchiveView):
            model = MyModel
            date_field = "pub_date"

```

## BuildableMonthArchiveView

```{eval-rst}
.. class:: BuildableMonthArchiveView(MonthArchiveView, BuildableMixin)

    Renders and builds a monthly archive showing all objects in a given month. Extended from Django's generic `MonthArchiveView <https://docs.djangoproject.com/en/1.9/ref/class-based-views/generic-date-based/#montharchiveview>`_.
    The base class has a number of options not documented here you should consult.

    .. attribute:: model

        A Django database model where the list of objects can be drawn
        with a ``Model.objects.all()`` query. Optional. If you want to provide
        a more specific list, define the ``queryset`` attribute instead.

    .. attribute:: queryset

        The list of objects that will be provided to the template. Can be
        any iterable of items, not just a Django queryset. Optional, but
        if this attribute is not defined the ``model`` attribute must be
        defined.

    .. attribute:: template_name

        The template you would like Django to render. You need
        to override this if you don't want to rely on the Django default,
        which is ``<model_name_lowercase>_archive_month.html``.

    .. method:: get_build_path()

        Used to determine where to build the detail page. Override this if you
        would like your detail page at a different location. By default it
        will be built at ``os.path.join(obj.get_url(), "index.html"``.

    .. method:: get_url()

        The URL at which the detail page should appear. By default it is /archive/ + the
        year in self.year_format + the month in self.month_format. An example would be /archive/2016/01/.

    .. py:attribute:: build_method

        An alias to the ``build_dated_queryset`` method used by the :doc:`management commands </managementcommands>`

    .. py:method:: build_dated_queryset()

        Writes the rendered HTML for all publishable dates to the build directory.

    .. py:method:: build_month(dt)

        Writes the rendered HTML for the provided month to the build directory.

    .. py:method:: unbuild_month(dt)

        Deletes the directory where the provided month's flat files are stored.

    **Example myapp/views.py**

    .. code-block:: python

        from myapp.models import MyModel
        from bakery.views import BuildableMonthArchiveView


        class ExampleMonthArchiveView(BuildableMonthArchiveView):
            model = MyModel
            date_field = "pub_date"

```

## BuildableDayArchiveView

```{eval-rst}
.. class:: BuildableDayArchiveView(DayArchiveView, BuildableMixin)

    Renders and builds a day archive showing all objects in a given day. Extended from Django's generic `DayArchiveView <https://docs.djangoproject.com/en/1.9/ref/class-based-views/generic-date-based/#dayarchiveview>`_.
    The base class has a number of options not documented here you should consult.

    .. attribute:: model

        A Django database model where the list of objects can be drawn
        with a ``Model.objects.all()`` query. Optional. If you want to provide
        a more specific list, define the ``queryset`` attribute instead.

    .. attribute:: queryset

        The list of objects that will be provided to the template. Can be
        any iterable of items, not just a Django queryset. Optional, but
        if this attribute is not defined the ``model`` attribute must be
        defined.

    .. attribute:: template_name

        The template you would like Django to render. You need
        to override this if you don't want to rely on the Django default,
        which is ``<model_name_lowercase>_archive_day.html``.

    .. method:: get_build_path()

        Used to determine where to build the detail page. Override this if you
        would like your detail page at a different location. By default it
        will be built at ``os.path.join(obj.get_url(), "index.html"``.

    .. method:: get_url()

        The URL at which the detail page should appear. By default it is /archive/ + the year in self.year_format + the
        month in self.month_format + the day in the self.day_format. An example would be /archive/2016/01/01/.

    .. py:attribute:: build_method

        An alias to the ``build_dated_queryset`` method used by the :doc:`management commands </managementcommands>`

    .. py:method:: build_dated_queryset()

        Writes the rendered HTML for all publishable dates to the build directory.

    .. py:method:: build_day(dt)

        Writes the rendered HTML for the provided day to the build directory.

    .. py:method:: unbuild_day(dt)

        Deletes the directory where the provided day's flat files are stored.

    **Example myapp/views.py**

    .. code-block:: python

        from myapp.models import MyModel
        from bakery.views import BuildableDayArchiveView


        class ExampleDayArchiveView(BuildableDayArchiveView):
            model = MyModel
            date_field = "pub_date"

```

## Buildable404View

```{eval-rst}
.. class:: Buildable404View(BuildableTemplateView)

    Renders and builds a simple 404 error page template as a flat file. Extended from the ``BuildableTemplateView`` above.
    The base class has a number of options not documented here you should consult.

    **All it does**

    .. code-block:: python

        from bakery.views import BuildableTemplateView


        class Buildable404View(BuildableTemplateView):
            build_path = '404.html'
            template_name = '404.html'

```

## BuildableRedirectView

```{eval-rst}
.. class:: BuildableRedirectView(RedirectView, BuildableMixin)

    Render and build a redirect. Extended from Django's generic
    `RedirectView <https://docs.djangoproject.com/en/dev/ref/class-based-views/base/#redirectview>`_.
    The base class has a number of options not documented here you should consult.

    .. py:attribute:: build_path

        The URL being requested, which will be published as a flatfile
        with a redirect away from it.

    .. py:attribute:: url

        The URL where redirect will send the user. Operates
        in the same way as the standard generic RedirectView.

    **Example myapp/views.py**

    .. code-block:: python

        from bakery.views import BuildableRedirectView


        class ExampleRedirectView(BuildableRedirectView):
            build_path = "mymodel/oldurl.html"
            url = '/mymodel/'
```
