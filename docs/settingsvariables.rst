Settings variables
==================

Configuration options for your ``settings.py``.

ALLOW_BAKERY_AUTO_PUBLISHING
----------------------------

.. envvar:: ALLOW_BAKERY_AUTO_PUBLISHING

    Decides whether the `AutoPublishingBuildableModel` is allowed to run the
    `publish` management command as part of its background task. True by default.

.. code-block:: python

    # So if you are in your dev environment and want to prevent
    # the task from publishing to s3, do this.
    ALLOW_BAKERY_AUTO_PUBLISHING = False

BUILD_DIR
---------

.. envvar:: BUILD_DIR

    The location where you want the flat files to be built.

.. code-block:: python

    BUILD_DIR = '/home/you/code/your-site/build/'

    # I like something a little snappier like...
    import os
    BUILD_DIR = os.path.join(__file__, 'build')

BAKERY_VIEWS
------------

.. envvar:: BAKERY_VIEWS

    The list of views you want to be built out as flat files when the ``build`` :doc:`management command </managementcommands>` is executed.

.. code-block:: python

    BAKERY_VIEWS = (
        'myapp.views.ExampleL­istView',
        'myapp.views.ExampleDe­tailView',
        'myapp.views.MyRSSView',
        'myapp.views.MySitemapView',
    )

AWS_BUCKET_NAME
---------------

.. envvar:: AWS_BUCKET_NAME

    The name of the `Amazon S3 "bucket" <http://aws.amazon.com/s3/>`_ on the Internet were you want to publish the flat files in your local ``BUILD_DIR``.

.. code-block:: python

    AWS_BUCK­ET_­NAME = 'your-buck­et'

AWS_ACCESS_KEY_ID
-----------------

.. envvar:: AWS_ACCESS_KEY_ID

    A part of your secret Amazon Web Services credentials. Necessary to upload files to S3.

.. code-block:: python

    AWS_ACCESS_KEY_ID = 'your-key'

AWS_SECRET_ACCESS_KEY
---------------------

.. envvar:: AWS_SECRET_ACCESS_KEY

    A part of your secret Amazon Web Services credentials. Necessary to upload files to S3.

.. code-block:: python

    AWS_SECRET_ACCESS_KEY = 'your-secret-key'

BAKERY_GZIP
-----------

.. envvar:: BAKERY_GZIP

    Opt in to automatic gzipping of your files in the build method and addition of
    the required headers when deploying to Amazon S3. Defaults to ``False``.

.. code-block:: python

    BAKERY_GZIP = True

GZIP_CONTENT_TYPES
------------------

.. envvar:: GZIP_CONTENT_TYPES

    A list of file mime types used to determine which files to add the
    'Content-Encoding: gzip' metadata header when syncing to Amazon S3.
    Defaults to include all 'text/css', 'text/html', 'application/javascript',
    'application/x-javascript', 'application/json' and 'application/xml'
    files.

    Only matters if you have set ``BAKERY_GZIP`` to ``True``.

.. code-block:: python

    # defaults to 'text/css', 'text/html', 'application/javascript',
    # 'application/x-javascript', 'application/json' and 'application/xml'
    # files.
    GZIP_CONTENT_TYPES = (
        'text/css',
        'text/html',
        'application/javascript',
        'application/x-javascript',
        'application/json',
        'application/xml'
    )

DEFAULT_ACL
---------------
.. envvar:: DEFAULT_ACL

    Set the access control level of the files uploaded. Defaults to 'public-read'

.. code-block:: python

    # defaults to 'public-read',
    DEFAULT_ACL = 'public-read'

BAKERY_CACHE_CONTROL
-----------

.. envvar:: BAKERY_CACHE_CONTROL

    Set cache-control headers based on content type. Headers are set using the ``max-age=`` format so the passed values should be in seconds (``'text/html': 900`` would result in a ``Cache-Control: max-age=900`` header for all ``text/html`` files). By default, none are set.

.. code-block:: python

    BAKERY_CACHE_CONTROL = {
        'text/html': 900,
        'application/javascript': 86400
    }