Management commands
===================

Custom `Django management commands <https://docs.djangoproject.com/en/dev/ref/django-admin/>`_ for
this library that help make things happen. 

build
-----

.. program:: build

    Bake out a site as flat files in the ``BUILD_DIR``.

.. cmdoption:: --build_dir <path>

   Specify the path of the build directory. Will use ``settings.BUILD_DIR`` by default.

.. cmdoption:: --skip-static

    Skip collecting the static files when building.

.. cmdoption:: --skip-media

    Skip collecting the media files when building.

.. code-block:: bash

    $ python manage.py build

buildserver
-----------

.. code-block:: bash

    $ python manage.py buildserver

publish
-------

.. code-block:: bash

    $ python manage.py publish

unbuild
-------

.. code-block:: bash

    $ python manage.py unbuild

unpublish
---------

.. code-block:: bash

    $ python manage.py unpublish
