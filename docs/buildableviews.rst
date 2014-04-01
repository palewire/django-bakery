Buildable views
===============

.. class:: BuildableTemplateView

    Renders and builds a simple template as a flat file. When inherited, the child class should include the following attributes.

    .. attribute:: build_path

        The target location of the built file in the ``BUILD_DIR``.
        ``index.html`` would place it at the built site's root.
        ``foo/index.html`` would place it inside a subdirectory.

    .. attribute:: template_name

        The name of the template you would like Django to render.
