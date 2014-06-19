Changelog
=========

0.6.0
-----

* An ``AutoPublishingBuildableModel`` that is able to use a Celery job queue to automatically build and publish objects when they are saved.
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
