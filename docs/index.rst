django-bakery
=============

A set of helpers for baking your Django site out as flat files

Why and what for
----------------

The code documented here is intended to make it easier to save every page gen­er­ated by a data­base-backed site as a flat file so you can host them us­ing a stat­ic file ser­vice like `Amazon S3 <http://en.wikipedia.org/wiki/Amazon_S3>`_.

At the Los Angeles Times Data Desk, we call this pro­cess “bak­ing.” It’s our path to cheap­, stable host­ing for simple sites. We've used it for pub­lish­ing `elec­tion res­ults <http://graphics.latimes.com/2012-election-gop-results-map-iowa/>`_, `timelines <http://timelines.latimes.com/complete-guide-lafd-hiring-controversy/>`_, `doc­u­ments <http://documents.latimes.com/barack-obama-long-form-birth-certificate/>`_, `in­ter­act­ive tables <http://spreadsheets.latimes.com/city-appointees-tied-garcetti/>`_, `spe­cial pro­jects <http://graphics.latimes.com/flight-from-rage/>`_ and `numerous <http://graphics.latimes.com/towergraphic-washington-landslide-victims/>`_ `other <http://graphics.latimes.com/how-fast-is-lafd/>`_ `things <http://graphics.latimes.com/picksheet-critics-picks-april-4-10-2014/>`_.

The sys­tem comes with some ma­jor ad­vant­ages, like:

1. No data­base crashes
2. Zero serv­er con­fig­ur­a­tion and up­keep
3. No need to op­tim­ize your app code
4. You don’t pay to host CPUs, only band­width
5. An off­line ad­min­is­tra­tion pan­el is more se­cure
6. Less stress (This one can change your life)

There are draw­backs. For one, you have to integrate the "bakery" in­to your code base. More im­port­ant, a flat site can only be so com­plex. No on­line data­base means your site is all read and no write, which means no user-gen­er­ated con­tent and no com­plex searches.

`Django's class-based views <https://docs.djangoproject.com/en/dev/topics/class-based-views/>`_ are at the heart of our approach. Putting all the pieces together is a little tricky at first, particularly if you haven't studied `the Django source code <https://github.com/django/django/tree/master/django/views/generic>`_ or lack experience `working with Python classes <http://www.diveintopython.net/object_oriented_framework/defining_classes.html>`_ in general. But once you figure it out, you can do all kinds of crazy things: Like configuring Django to bake out your entire site with a single command.

Here's how.

Documentation
-------------

.. toctree::
   :maxdepth: 3

   gettingstarted
   commonchallenges
   buildableviews
   buildablemodels
   buildablefeeds
   settingsvariables
   managementcommands
   changelog
   credits

Considering alternatives
------------------------

If you are seeking to "bake" out a very simple site, maybe you don't have a database or only a single page, it is quicker
to try `Tarbell <http://tarbell.tribapps.com/>`_ or `Frozen-Flask <https://pythonhosted.org/Frozen-Flask/>`_, which don't require all 
the overhead of a full Django installation. 

This library is better to suited for projects that require a database, want to take advantage of other Django features (like the administration panel)
or require more complex views.

Contributing
------------

* Code repository: `https://github.com/datadesk/django-bakery <https://github.com/datadesk/django-bakery>`_
* Issues: `https://github.com/datadesk/django-bakery/issues <https://github.com/datadesk/django-bakery/issues>`_
* Packaging: `https://pypi.python.org/pypi/django-bakery <https://pypi.python.org/pypi/django-bakery>`_
* Testing: `https://travis-ci.org/datadesk/django-bakery <https://travis-ci.org/datadesk/django-bakery>`_
* Coverage: `https://coveralls.io/r/datadesk/django-bakery <https://coveralls.io/r/datadesk/django-bakery>`_
