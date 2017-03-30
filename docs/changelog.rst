Changelog
=========

0.9.0
-----

* Replaced ``boto`` dependency with ``boto3`` and refactored publish command to adjust
* More verbose logging of gzipped paths during build routine
* Reduced some logging in management commands when verbosity=0
* Added testing for Django 1.11

0.8.14
------

* Management command drops ``six.print`` for ``self.output.write``
* Only strip first slash of urls with lstrip

0.8.13
------

* Fixed bug in ``BuildableDayArchiveView`` argument handling.

0.8.12
------

* Added ``create_request`` method to the base view mixin so there's a clearer method for overriding the creation of a ``RequestFactory`` when building views.

0.8.10
------

* Expanded default ``GZIP_CONTENT_TYPES`` to cover SVGs and everything else recommended by the `HTML5 boilerplate guides <https://github.com/h5bp/server-configs-apache>`_.

0.8.9
-----

* Removed ``CommandError`` exception handling in ``build`` command because errors should never pass silently, unless explicitly silenced.

0.8.8
-----

* Django 1.10 support and testing

0.8.7
-----

* ``get_month`` and ``get_year`` fix on the month archive view

0.8.6
-----

* ``get_year`` fix on the year archive view.

0.8.5
-----

* ``get_absolute_url`` bug fix on detail view.

0.8.3
-----

* Added support for ``AWS_S3_HOST`` variable to override the default with connecting to S3 via boto.

0.8.2
-----

* Upgraded to Django new style of management command options.

0.8.1
-----

* Patch to allow for models to be imported with ``django.contrib.contenttypes`` being installed.

0.8.0
-----

* Added new date-based archive views BuildableArchiveIndexView, BuildableYearArchiveView, BuildableMonthArchiveView, BuildableDayArchiveView
* get_url method on the BuildableDetailView now raises a ImproperlyConfigured error
* Refactored views into separate files

0.7.8
-----

* Improved error handling and documentation of BuildableDetailView's ``get_url`` method.

0.7.7
-----

* Patch provided backwards compatibility to a boto bug fix.

0.7.6
-----

* Patched ``set_kwargs`` to override the key name of the slug when it is configured by the detail view's ``slug_field`` setting

0.7.5
-----

* BAKERY_CACHE_CONTROL settings variable and support
* Better tests for publish and unpublish
* Delete operations in publish and unpublish command breaks keys into batches to avoid S3 errors on large sets

0.7.4
-----

* Fixed content_type versus mimetype bug in the static views for Django 1.7 and 1.8
* A few other small Python 3 related bugs

0.7.3
-----

* Added a ``--no-delete`` option to the ``publish`` management command.
* Fixed testing in Django 1.7

0.7.1
-----

* Added ``BuildableRedirectView``

0.6.4
-----

* Added ``BuildableFeed`` for RSS support

0.6.3
-----

* Changed ``AutoPublishingBuildableModel`` to commit to the database before triggering a task
* Changed celery tasks to accept primary keys instead of model objects

0.6.0
-----

* An ``AutoPublishingBuildableModel`` that is able to use a Celery job queue to automatically build and publish objects when they are saved
* Refactored ``build`` management command to allow for its different tasks to be more easily overridden
* Added a ``--keep-build-dir`` option to the ``build`` command.

0.5.0
-----
* Refactored the ``publish`` and ``unpublish`` management commands to use boto instead of s3cmd.
* ``build`` and ``publish`` management commands use file mimetypes instead of a regex on the filename to decide if a file will be gzipped.
* ``publish`` management command includes --force and --dry-run uploads to force an upload of all file, regardless of changes, and to print output without uploading files, respectively.
* ``publish`` management command now pools uploads to increase speed

0.4.2
-----

* Added a ``get_content`` method to all of the buildable views to make it easier to build pages that don't require a template, like JSON outputs

0.4.1
-----

* Bug fix with calculating Python version in the views in v0.4.0

0.4.0
-----

* Added optional gzip support to build routine for Amazon S3 publishing (via `@emamd <https://twitter.com/emamd>`_)
* Mixin buildable view with common methods

0.3.0
-----

* Python 3 support
* Unit tests
* Continuous integration test by Travis CI
* Coverage reporting by Coveralls.io
* PEP8 compliance
* PyFlakes compliance
* Refactored ``buildserver`` management command to work with latest versions of Django

0.2.0
-----

* Numerous bug fixes

0.1.0
-----

* `Initial release <http://datadesk.latimes.com/posts/2012/03/introducing-django-bakery/>`_
