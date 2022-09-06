<pre><code>                   
                # # # # #
              __#_#_#_#_#__
             {_` ` ` ` ` `_}
            _{_._._._._._._}_
           {_  D J A N G O  _}
          _{_._._._._._._._._}_
         {_    B A K E R Y    _}
     .---{_._._._._._._._._._._}---.
    (   `"""""""""""""""""""""""`   )
     `~~~~~~~~~~~~~~~~~~~~~~~~~~~~~`</code></pre>

A set of helpers for baking your Django site out as flat files

* Documentation: [http://django-bakery.rtfd.org](http://django-bakery.rtfd.org)
* Issues: [https://github.com/datadesk/django-bakery/issues](https://github.com/datadesk/django-bakery/issues)
* Packaging: [https://pypi.python.org/pypi/django-bakery](https://pypi.python.org/pypi/django-bakery)
* Testing: [https://travis-ci.org/datadesk/django-bakery](https://travis-ci.org/datadesk/django-bakery)
* Coverage: [https://coveralls.io/r/datadesk/django-bakery](https://coveralls.io/r/datadesk/django-bakery)
* The dream, in Powerpoint form: [http://lat.ms/bakery-talk](http://lat.ms/bakery-talk)

## Features

* Models, views and management commands that will build your site as flat files.
* Management commands to sync your flat files with a bucket on Amazon S3.
* Optional integration of a Celery job queue to automatically build and publish model objects when they are saved