# Getting started

## Installation

Before you begin, you should have a Django project [created and configured](https://docs.djangoproject.com/en/dev/intro/install/).

Install our library from PyPI, like so:

```bash
$ pip install django-bakery
```

Edit your `settings.py` and add the app to your `INSTALLED_APPS` list.

```python
INSTALLED_APPS = (
    # ...
    # other apps would be above this of course
    # ...
    "bakery",
)
```

## Configuration

Also in `settings.py`, add a build directory where the site will be built as flat files. This is where bakery will create the static version of your website that can be hosted elsewhere.

```python
BUILD_DIR = "/home/you/code/your-site/build/"
```

The trickiest step is to refactor your views to inherit our
{doc}`buildable class-based views </buildableviews>`. They are similar to
Django's [generic class-based views](https://docs.djangoproject.com/en/dev/topics/class-based-views/),
except extended to know how to automatically build themselves as flat files.

Here is a list view and a detail view using our system.

```python
from yourapp.models import DummyModel
from bakery.views import BuildableDetailView, BuildableListView


class DummyListView(BuildableListView):
    """
    Generates a page that will feature a list linking to detail pages about
    each object in the queryset.
    """

    queryset = DummyModel.live.all()


class DummyDetailView(BuildableDetailView):
    """
    Generates a separate HTML page for each object in the queryset.
    """

    queryset = DummyModel.live.all()
```

If you've never seen class-based views before, you should study up in
[the Django docs](https://docs.djangoproject.com/en/dev/topics/class-based-views/)
because we aren't going to rewrite their documentation here.

If you've already seen class-based views and decided you dislike them,
[you're not alone](http://lukeplant.me.uk/blog/posts/djangos-cbvs-were-a-mistake/)
but you'll have to take our word that they're worth the trouble in this case. You'll see why soon enough.

After you’ve converted your views, add them to a list in `settings.py` where
all buildable views should be recorded as in the `BAKERY_VIEWS` variable.

```python
BAKERY_VIEWS = (
    "yourapp.views.DummyListView",
    "yourapp.views.DummyDetailView",
)
```

## Execution

Then run the management command that will bake them out.

```bash
$ python manage.py build
```

This will create a copy of every page that your views support in the `BUILD_DIR`.
You can review its work by firing up the `buildserver`, which will locally
host your flat files in the same way the Django’s `runserver` hosts your
dynamic database-driven pages.

```bash
$ python manage.py buildserver
```

To publish the site on Amazon S3, all that’s necessary yet is to create a
"bucket" inside Amazon's service. You can go to [aws.amazon.com/s3/](http://aws.amazon.com/s3/)
to set up an account. If you need some basic instructions you can find
them [here](http://docs.amazonwebservices.com/AmazonS3/latest/gsg/GetStartedWithS3.html?r=9703).
Then set your bucket name in `settings.py`.

```python
AWS_BUCKET_NAME = "your-bucket"
```

While you're in there, you also need to set your credentials.

```python
AWS_ACCESS_KEY_ID = "your-key"
AWS_SECRET_ACCESS_KEY = "your-secret-key"  # pragma: allowlist secret
```

Finally, now that everything is set up, publishing your files to S3 is as simple as:

```bash
$ python manage.py publish
```

You should be able to visit your bucket's live URLs and see the site in action.
To make your bucket act more like a normal website or connect it to a domain you
control [follow these instructions](http://docs.aws.amazon.com/AmazonS3/latest/dev/HowDoIWebsiteConfiguration.html).

## Optimization

If you are publishing to S3, you can reduce the size of HTML, JavaScript and CSS files
by having bakery compress them using [gzip](http://en.wikipedia.org/wiki/Gzip) as they are uploaded. Read more about this feature [here](http://www.savjee.be/2014/03/Jekyll-to-S3-deploy-script-with-gzip/), [here](http://sukharevd.net/gzipping-website-in-amazon-s3-bucket.html) or [here](http://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/ServingCompressedFiles.html#CompressedS3).

Getting started is as simple as returning to `settings.py` and adding the following:

```python
BAKERY_GZIP = True
```

Then rebuilding and publishing your files.

```bash
$ python manage.py build
$ python manage.py publish
```
