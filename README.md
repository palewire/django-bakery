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

* Documentation: [palewi.re/docs/django-bakery](https://palewi.re/docs/django-bakery/)
* Issues: [https://github.com/datadesk/django-bakery/issues](https://github.com/datadesk/django-bakery/issues)
* Packaging: [https://pypi.python.org/pypi/django-bakery](https://pypi.python.org/pypi/django-bakery)
* The dream, in Powerpoint form: [palewi.re/docs/django-bakery/_static/the-dream.pdf](https://palewi.re/docs/django-bakery/_static/the-dream.pdf)

## Features

* Models, views and management commands that will build your site as flat files.
* Management commands to sync your flat files with a bucket on Amazon S3.
* Optional integration of a Celery job queue to automatically build and publish model objects when they are saved
