Buildable views
===============

.. class:: BuildableTemplateView

    Renders and builds a simple template as a flat file. Extended from Django's 
    generic `TemplateView <https://docs.djangoproject.com/en/dev/ref/class-based-views/base/#django.views.generic.base.TemplateView>`_.

    .. attribute:: build_path

        The target location of the built file in the ``BUILD_DIR``.
        ``index.html`` would place it at the built site's root.
        ``foo/index.html`` would place it inside a subdirectory. Required.

    .. attribute:: template_name

        The name of the template you would like Django to render. Required.


.. class:: BuildableListView

    Render and builds a page about a list of objects. Extended from Django's 
    generic `ListView <https://docs.djangoproject.com/en/dev/ref/class-based-views/generic-display/#django.views.generic.list.ListView>`_.

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

    .. code-block:: python

        import os
        from django.conf import settings
        from myapp.models import MyModel
        from bakery.views import BuildableListView


        class ExampleListView(BuildableListView):
            model = MyModel
            template_name = 'mymodel_list.html'


        class DifferentExampleListView(BuildableListView):
            queryset = MyModel.objects.filter(is_published=True)
            template_name = 'mymodel_list.html'
            build_path = os.path.join(settings.BUILD_DIR, 'mymodel', 'index.html')


.. class:: BuildableDetailView

    Render and build a "detail" page about an object or a series of pages
    about a list of objects. Extended from Django's generic `DetailView <https://docs.djangoproject.com/en/dev/ref/class-based-views/generic-display/#detailview>`_.

    .. attribute:: queryset

        The Django model instance the objects are looked up from.

    .. attribute:: template_name

        The name of the template you would like Django to render. You need
        to override this if you don't want to rely on the Django defaults.
