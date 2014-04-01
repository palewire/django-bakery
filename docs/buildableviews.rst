Buildable views
===============

.. class:: BuildableTemplateView

    Renders and builds a simple template as a flat file. When inherited, the child class should include the following attributes.

    .. attribute:: build_path

        The target location of the built file in the ``BUILD_DIR``.
        ``index.html`` would place it at the built site's root.
        ``foo/index.html`` would place it inside a subdirectory. Required.

    .. attribute:: template_name

        The name of the template you would like Django to render. Required.


.. class:: BuildableListView

    Render and builds a page about a list of objects.

    .. attribute:: model

        A Django database model where the list of objects can be drawn
        with a ``Model.objects.all`` query. Optional. If you want to provide
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
