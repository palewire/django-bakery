# Getting started

## Installation

Before you begin, you should have a Django project [created and configured](https://docs.djangoproject.com/en/dev/intro/install/).

In­stall our library from PyPI, like so:

```bash
$ pip install django-bakery
```

Edit your `settings.py` and add the app to your `INSTALLED_APPS` list.

```python
IN­STALLED_APPS = (
    # ...
    # other apps would be above this of course
    # ...
    'bakery',
)
```

## Configuration

Also in `settings.py`, add a build directory where the site will be built as flat files. This is where bakery will create the static version of your website that can be hosted elsewhere.

```python
BUILD_DIR = '/home/you/code/your-site/build/'
```

The trickiest step is to re­fact­or your views to in­her­it our
{doc}`buildable class-based views </buildableviews>`. They are similar to
Django's [generic class-based views](https://docs.djangoproject.com/en/dev/topics/class-based-views/),
except extended to know how to auto­mat­ic­ally build them­selves as flat files.

Here is a list view and a de­tail view us­ing our sys­tem.

```python
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
```

If you've never seen class-based views before, you should study up in
[the Django docs](https://docs.djangoproject.com/en/dev/topics/class-based-views/)
because we aren't going to rewrite their documentation here.

If you've already seen class-based views and decided you dislike them,
[you're not alone](http://lukeplant.me.uk/blog/posts/djangos-cbvs-were-a-mistake/)
but you'll have to take our word that they're worth the trouble in this case. You'll see why soon enough.

After you’ve con­ver­ted your views, add them to a list in `settings.py` where
all build­able views should be recorded as in the `BAKERY_VIEWS` variable.

```python
BAKERY_VIEWS = (
    'yourapp.views.DummyL­istView',
    'yourapp.views.DummyDe­tailView',
)
```

## Execution

Then run the man­age­ment com­mand that will bake them out.

```bash
$ python manage.py build
```

This will create a copy of every page that your views support in the `BUILD_DIR`.
You can re­view its work by fir­ing up the `buildserver`, which will loc­ally
host your flat files in the same way the Django’s `runserver` hosts your
dynamic data­base-driv­en pages.

```bash
$ python manage.py buildserver
```

To pub­lish the site on Amazon S3, all that’s ne­ces­sary yet is to cre­ate a
"buck­et" inside Amazon's service. You can go to [aws.amazon.com/s3/](http://aws.amazon.com/s3/)
to set up an ac­count. If you need some ba­sic in­struc­tions you can find
them [here](http://docs.amazonwebservices.com/AmazonS3/latest/gsg/GetStartedWithS3.html?r=9703).
Then set your buck­et name in `settings.py`.

```python
AWS_BUCK­ET_­NAME = 'your-buck­et'
```

While you're in there, you also need to set your credentials.

```python
AWS_ACCESS_KEY_ID = 'your-key'
AWS_SECRET_ACCESS_KEY = 'your-secret-key'
```

Fi­nally, now that everything is set up, pub­lish­ing your files to S3 is as simple as:

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
