Changelog
=========

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
