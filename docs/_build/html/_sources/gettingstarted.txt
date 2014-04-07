Getting started
===============

Before you begin, you should have a Django project `created and configured <https://docs.djangoproject.com/en/dev/intro/install/>`_.

In­stall our library from PyPI, like so:

.. code-block:: bash

    $ pip install django-bakery

Edit your ``settings.py`` and add the app to your ``INSTALLED_APPS`` list.

.. code-block:: python

    IN­STALLED_APPS = (
        # ...
        # other apps would be above this of course
        # ...
        'bakery',
    )

Also in ``settings.py``, add a build directory where the site will be built as flat files. This is where bakery will create the static version of your website that can be hosted elsewhere.

.. code-block:: python

    BUILD_DIR = '/home/you/code/your-site/build/'

The trickest step is to re­fact­or your views to in­her­it our :doc:`buildable class-based views </buildableviews>`. They are similar to Django's `generic class-based views <https://docs.djangoproject.com/en/dev/topics/class-based-views/>`_, except extended to know how to auto­mat­ic­ally build them­selves as flat files. Here is a list view and a de­tail view us­ing our sys­tem. 

If you've never seen class-based views before, you should study up in `the Django docs <https://docs.djangoproject.com/en/dev/topics/class-based-views/>`_ because we don't aren't going to rewrite their documentation here. If you've already seen class-based views and decided you dislike them, `you're not alone <http://lukeplant.me.uk/blog/posts/djangos-cbvs-were-a-mistake/>`_ but you'll have to take our word that they're worth the trouble in this case. You'll see why soon enough. 

.. code-block:: django

    from yourapp.mod­els im­port Dummy­Mod­el
    from bakery.views im­port Build­able­De­tailView, Build­ableL­istView


    class DummyL­istView(Build­ableL­istView):
        """
        Generates a page that will feature a list linking to detail pages about
        each object in the queryset.
        """
        queryset = Dummy­Mod­el.live.all()


    class DummyDe­tailView(Build­able­De­tailView):
        """
        Generates a separate HTML page for each object in the queryset.
        """
        queryset = Dummy­Mod­el.live.all()

After you’ve con­ver­ted your views, add them to a list in ``settings.py`` where all build­able views will be collected.

.. code-block:: python

    BAKERY_VIEWS = [
        'yourapp.views.DummyL­istView',
        'yourapp.views.DummyDe­tailView',
    ]

Then run the man­age­ment com­mand that will bake them out. 

.. code-block:: bash

    $ python manage.py build

This will create a copy of every page that your views support in the ``BUILD_DIR``. You can re­view its work by fir­ing up the ``buildserver``, which will loc­ally host your flat files in the same way the Django’s ``runserver`` hosts your dynamic data­base-driv­en pages.

.. code-block:: bash

    $ python manage.py buildserver

To pub­lish the site on Amazon S3, all that’s ne­ces­sary yet is to cre­ate a "buck­et" inside Amazon's service. You can go to `aws.amazon.com/s3/ <http://aws.amazon.com/s3/>`_ to set up an ac­count. If you need some ba­sic in­struc­tions you can find them `here <http://docs.amazonwebservices.com/AmazonS3/latest/gsg/GetStartedWithS3.html?r=9703>`_. Then set your buck­et name in ``settings.py``.

.. code-block:: python

    AWS_BUCK­ET_­NAME = 'your-buck­et'

Next, in­stall `s3cmd <http://s3tools.org/s3cmd>`_, a util­ity we’ll use to move files back and forth between your desktop and S3. In Ubuntu, that’s as simple as:

.. code-block:: bash

    $ sudo apt-get install s3cmd

If you’re us­ing Mac or Win­dows, you’ll need to down­load `this file <http://s3tools.org/download>`_ and fol­low the in­stall­a­tion in­struc­tions you find there.

Once it’s in­stalled, we need to con­fig­ure s3cmd with your Amazon lo­gin cre­den­tials. Go to Amazon’s `se­cur­ity cre­den­tials page <http://aws-portal.amazon.com/gp/aws/developer/account/index.html?action=access-key>`_ and get your ac­cess key and secret ac­cess key. Then, from your ter­min­al, run:

.. code-block:: bash

    $ s3cmd --configure

Fi­nally, now that everything is set up, pub­lish­ing your files to S3 is as simple as:

.. code-block:: bash

    $ python manage.py publish

Now you should be able to vist your bucket's live URLs and see the site in action. To make your bucket act more like a normal website or connect it to a domain you control `follow these instructions <http://docs.aws.amazon.com/AmazonS3/latest/dev/HowDoIWebsiteConfiguration.html>`_.
