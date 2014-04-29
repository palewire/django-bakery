Settings variables
==================

Configuration options for your ``settings.py``.

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

BAKERY_GZIP
---------------

.. envvar:: BAKERY_GZIP

    Opt in to automatic gzipping of your files in the build method and addition of
    the required headers when deploying to Amazon S3. Defaults to ``False``.

.. code-block:: python

    BAKERY_GZIP = True

GZIP_FILE_MATCH
---------------

.. envvar:: GZIP_FILE_MATCH

    An uncompiled regular expression used to determine which files to have the
    'Content-Encoding: gzip' metadata header added when syncing to Amazon S3. 
    Defaults to include all .html, .xml, .css, .js and .json files.

    Only matters if you have set ``BAKERY_GZIP`` to ``True``.

.. code-block:: python

    # defaults to all .html, .xml, .css, .js and .json files
    GZIP_FILE_MATCH = '(\.html|\.xml|\.css|\.js|\.json)$'
