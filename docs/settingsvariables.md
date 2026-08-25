# Settings variables

Configuration options for your `settings.py`.

## ALLOW_BAKERY_AUTO_PUBLISHING

```{eval-rst}
.. envvar:: ALLOW_BAKERY_AUTO_PUBLISHING

    Decides whether the `AutoPublishingBuildableModel` is allowed to run the
    `publish` management command as part of its background task. True by default.
```

```python
# So if you are in your dev environment and want to prevent
# the task from publishing to s3, do this.
ALLOW_BAKERY_AUTO_PUBLISHING = False
```

## BUILD_DIR

```{eval-rst}
.. envvar:: BUILD_DIR

    The location on the filesystem where you want the flat files to be built.
```

```python
BUILD_DIR = "/home/you/code/your-site/build/"

# I like something a little snappier like...
import os

BUILD_DIR = os.path.join(__file__, "build")
```

## BAKERY_FILESYSTEM

```{eval-rst}
.. envvar:: BAKERY_FILESYSTEM

    Files are built using `fsspec <https://filesystem-spec.readthedocs.io/>`_,
    which provides the filesystem interface used by Bakery. The default setting
    is the local filesystem backend. If you don't set the variable, it operates
    as follows:

    .. code-block:: python

        BAKERY_FILESYSTEM = "osfs:///"

    The supported legacy configuration strings are ``osfs:///`` for the local
    filesystem and ``mem://`` for an in-memory filesystem. Root paths appended
    to either URL keep all Bakery output below that root.

    With the unrooted default ``osfs:///`` backend, ``BUILD_DIR`` must name a
    directory. Empty and ``"."`` build directories are only safe with a rooted
    backend URL.

    .. code-block:: python

        BAKERY_FILESYSTEM = "mem://"

    Amazon S3 support is optional. Install it before configuring an S3 backend:

    .. code-block:: console

        python -m pip install "django-bakery[s3]"

    An S3 URL contains a bucket and an optional key prefix. Bakery normalizes
    the prefix and resolves ``BUILD_DIR`` and every generated path below it:

    .. code-block:: python

        BAKERY_FILESYSTEM = "s3://my-bucket"

        # With BUILD_DIR = "site", output starts at
        # s3://my-bucket/releases/current/site/
        BAKERY_FILESYSTEM = "s3://my-bucket/releases/current"

    The configured bucket must already exist and Bakery must be able to access
    it. Bakery checks this when a build or unbuild starts, rather than while
    Django loads the application. Bakery never creates or deletes S3 buckets.
    When a build or unbuild targets a bucket root, Bakery removes the selected
    output objects one by one while preserving the bucket and its
    configuration, including policies and website settings. A configured prefix
    is cleaned independently and never removes sibling prefixes.

    Direct S3 output sets each object's content type from its filename. When
    ``BAKERY_GZIP`` creates compressed output, Bakery also sets
    ``Content-Encoding: gzip`` while retaining the original content type.
    Copied files, including files that already have a compression suffix, only
    receive a content type.

    `s3fs <https://s3fs.readthedocs.io/>`_ uses the standard AWS credential
    and configuration chain. Configure credentials, region, profiles, and
    custom endpoints outside Django with the mechanisms supported by the AWS
    SDK, such as ``AWS_PROFILE``, ``AWS_DEFAULT_REGION``, and
    ``AWS_ENDPOINT_URL``. The similarly named Django settings below configure
    the separate ``publish`` command, not this direct filesystem backend.

    The S3 URL accepts only the bucket and optional prefix; query-string storage
    options are not supported. Arbitrary fsspec URLs and historical
    PyFilesystem plugin URLs also remain unsupported. This adapter intentionally
    covers only the rooted filesystem operations used by ``build`` and
    ``unbuild``.

    Releases before 0.13 used `PyFilesystem2 <https://docs.pyfilesystem.org/>`_.
    Upgrading from those releases requires the following steps:

    * Uninstall ``fs``, along with any PyFilesystem backend such as ``fs-s3fs``.
      They are no longer used and their ``pkg_resources`` imports fail with
      setuptools 81 and later.
    * Keep ``osfs:///`` and ``mem://`` settings as they are. Both continue to
      work, including root paths appended to either URL.
    * Replace an ``s3://`` setting that relied on ``fs-s3fs`` by installing
      ``django-bakery[s3]``. The URL syntax is unchanged, but credentials now
      come from the AWS chain described above rather than from the URL.
    * Replace any other PyFilesystem plugin URL. Unsupported URLs raise a
      ``ValueError`` when Django loads the ``bakery`` app.

```

## BAKERY_VIEWS

```{eval-rst}
.. envvar:: BAKERY_VIEWS

    The list of views you want to be built out as flat files when the ``build`` :doc:`management command </managementcommands>` is executed.
```

```python
BAKERY_VIEWS = (
    "myapp.views.ExampleListView",
    "myapp.views.ExampleDetailView",
    "myapp.views.MyRSSView",
    "myapp.views.MySitemapView",
)
```

## AWS_BUCKET_NAME

```{eval-rst}
.. envvar:: AWS_BUCKET_NAME

    The name of the `Amazon S3 "bucket" <http://aws.amazon.com/s3/>`_ on the Internet were you want to publish the flat files in your local ``BUILD_DIR``.
```

```python
AWS_BUCKET_NAME = "your-bucket"
```

## AWS_ACCESS_KEY_ID

```{eval-rst}
.. envvar:: AWS_ACCESS_KEY_ID

    A part of your secret Amazon Web Services credentials. Necessary to upload files to S3.
```

```python
AWS_ACCESS_KEY_ID = "your-key"
```

## AWS_SECRET_ACCESS_KEY

```{eval-rst}
.. envvar:: AWS_SECRET_ACCESS_KEY

    A part of your secret Amazon Web Services credentials. Necessary to upload files to S3.
```

```python
AWS_SECRET_ACCESS_KEY = "your-secret-key"  # pragma: allowlist secret
```

## AWS_REGION

```{eval-rst}
.. envvar:: AWS_REGION

    The name of the Amazon Web Services' region where the S3 bucket is stored. Results depend on the endpoint and region, but if you are not using the default ``us-east-1`` region you may need to set this variable.
```

```python
AWS_REGION = "us-west-2"
```

## AWS_S3_ENDPOINT

```{eval-rst}
.. envvar:: AWS_S3_ENDPOINT

    The URL to use when connecting with Amazon Web Services' S3 system. If the
    setting is not provided the boto package's default is used.
```

```python
# Substitute in Amazon's accelerated upload service
AWS_S3_ENDPOINT = "https://s3-accelerate.amazonaws.com"
# Specify the region of the bucket to work around bugs with S3 in certain version of boto
AWS_S3_ENDPOINT = "https://s3-%s.amazonaws.com" % AWS_REGION
```

## BAKERY_GZIP

```{eval-rst}
.. envvar:: BAKERY_GZIP

    Opt in to automatic gzipping of your files in the build method and addition of
    the required headers when deploying to Amazon S3. Defaults to ``False``.
```

```python
BAKERY_GZIP = True
```

## GZIP_CONTENT_TYPES

```{eval-rst}
.. envvar:: GZIP_CONTENT_TYPES

    A list of file mime types used to determine which files to add the
    'Content-Encoding: gzip' metadata header when syncing to Amazon S3.

    Defaults to include all 'text/css', 'text/html', 'application/javascript',
    'application/x-javascript' and everything else recommended by the HTML5
    `boilerplate guide <https://github.com/h5bp/server-configs-apache>`_.

    Only matters if you have set ``BAKERY_GZIP`` to ``True``.
```

```python
GZIP_CONTENT_TYPES = (
    "application/atom+xml",
    "application/javascript",
    "application/json",
    "application/ld+json",
    "application/manifest+json",
    "application/rdf+xml",
    "application/rss+xml",
    "application/schema+json",
    "application/vnd.geo+json",
    "application/vnd.ms-fontobject",
    "application/x-font-ttf",
    "application/x-javascript",
    "application/x-web-app-manifest+json",
    "application/xhtml+xml",
    "application/xml",
    "font/eot",
    "font/opentype",
    "image/bmp",
    "image/svg+xml",
    "image/vnd.microsoft.icon",
    "image/x-icon",
    "text/cache-manifest",
    "text/css",
    "text/html",
    "text/javascript",
    "text/plain",
    "text/vcard",
    "text/vnd.rim.location.xloc",
    "text/vtt",
    "text/x-component",
    "text/x-cross-domain-policy",
    "text/xml",
)
```

## DEFAULT_ACL

```{eval-rst}
.. envvar:: DEFAULT_ACL

    Set the access control level of the files uploaded. Defaults to 'public-read'
```

```python
# defaults to 'public-read',
DEFAULT_ACL = "public-read"
```

## BAKERY_CACHE_CONTROL

```{eval-rst}
.. envvar:: BAKERY_CACHE_CONTROL

    Set cache-control headers based on content type. Headers are set using the ``max-age=`` format so the passed values should be in seconds (``'text/html': 900`` would result in a ``Cache-Control: max-age=900`` header for all ``text/html`` files). By default, none are set.
```

```python
BAKERY_CACHE_CONTROL = {"text/html": 900, "application/javascript": 86400}
```
