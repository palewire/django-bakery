Management commands
===================

Custom `Django management commands <https://docs.djangoproject.com/en/dev/ref/django-admin/>`_ for
this library that help make things happen. 

build
-----

Bake out a site as flat files in the build directory.

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

Starts a variation of Django's `runserver <https://docs.djangoproject.com/en/dev/ref/django-admin/#runserver-port-or-address-port>`_ designed to serve the static files you've built
in the build directory.

.. code-block:: bash

    $ python manage.py buildserver

publish
-------

Syncs the build directory with your Amazon S3 bucket using ``s3cmd``.

.. cmdoption:: --aws-bucket-name <name>

    Specify the AWS bucket to sync with. Will use settings.AWS_BUCKET_NAME by default.

.. cmdoption:: --build_dir <path>

    Specify the path of the build directory. Will use settings.BUILD_DIR by default.

.. cmdoption:: --config <path>

    Specify the path of an s3cmd configuration file. Will use ``~/.s3cmd`` by default.

.. code-block:: bash

    $ python manage.py publish

unbuild
-------

Empties the build directory.

.. code-block:: bash

    $ python manage.py unbuild

unpublish
---------

Empties the Amazon S3 bucket defined in ``settings.py``.

.. code-block:: bash

    $ python manage.py unpublish
