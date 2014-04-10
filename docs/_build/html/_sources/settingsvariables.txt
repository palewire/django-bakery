Settings variables
==================

Configuration options for your ``settings.py``.

BUILD_DIR
---------

The location where you want the flat files to be built.

.. code-block:: python

    BUILD_DIR = '/home/you/code/your-site/build/'

I like something a little snappier like:

.. code-block:: python

    import os
    BUILD_DIR = os.path.join(__file__, 'build')

BAKERY_VIEWS
------------

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

The name of the `Amazon S3 "bucket" <http://aws.amazon.com/s3/>`_ on the Internet were you want to publish the flat files in your local ``BUILD_DIR``.

.. code-block:: python

    AWS_BUCK­ET_­NAME = 'your-buck­et'

