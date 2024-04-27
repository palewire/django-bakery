## Configuring where detail pages are built

If you are seeking to publish a detail page for each record in a database model,
our recommended way is using the {ref}`BuildableDetailView <buildable-detail-view>`.

When the view is executed via bakery's {ref}`standard build process <build>`, it will loop
through each object in the table and build a corresponding page at a path determined by
the view's `get_url` method.

You can override `get_url` to build the pages anywhere you want, but the easiest
route is by configuring Django's standard [get_absolute_url](https://docs.djangoproject.com/en/1.9/ref/models/instances/#get-absolute-url)
method on the model, which is where `get_url` looks by default.

Here's an example. Let's start with a model that will contain a record for each
of America's 50 states. Notice how we have defined Django's standard `get_absolute_url`
method to return a URL that features each state's unique postal code.

```{code-block} python
:emphasize-lines: 9,10

from django.db im­port mod­els
from bakery.mod­els im­port Build­ableMod­el


class State(Build­ableMod­el):
    name = mod­els.Char­Field(max_length=100)
    postal_code = models.CharField(max_length=2, unique=True)

    def get_absolute_url(self):
        return '/%s/' % self.postal_code
```

That model is then connected to a `BuildableDetailView` that can create a page
for every state.

```python
from myapp.models import State
from bakery.views import BuildableDetailView


class StateDetailView(BuildableDetailView):
    model = State
    template_name = 'state_detail.html'
```

As described in the {doc}`getting started guide </gettingstarted>`, that view will need to be added
to the `BAKERY_VIEWS` list in `settings.py`.

Now, because the URL has been preconfigured with `get_absolute_url`, all 50 pages
can be built with the standard management command (assuming your settings have
been properly configured).

```bash
$ python manage.py build
```

That will create pages like this in the build directory.

```bash
build/AL/index.html
build/AK/index.html
build/AR/index.html
build/AZ/index.html
build/CA/index.html
build/CO/index.html
... etc ...
```

If you wanted to build objects using a pattern independent of the model, you can instead
override the `get_url` method on the `BuildableDetailView`.

```{code-block} python
:emphasize-lines: 9,10

from myapp.models import State
from bakery.views import BuildableDetailView


class ExampleDetailView(BuildableDetailView):
    model = State
    template_name = 'state_detail.html'

    def get_url(self, obj):
        return '/my-fancy-pattern/state/%s/' % obj.postal_code
```

That will create pages like this in the build directory.

```bash
build/my-fancy-pattern/state/AL/index.html
build/my-fancy-pattern/state/AK/index.html
build/my-fancy-pattern/state/AR/index.html
build/my-fancy-pattern/state/AZ/index.html
build/my-fancy-pattern/state/CA/index.html
build/my-fancy-pattern/state/CO/index.html
... etc ...
```

## Building JSON instead of HTML

Suppose you have a view the acts like an API, generating a small snippet
of JSON. In this case,
[the official Django documentation recommends the following](https://docs.djangoproject.com/en/1.6/topics/class-based-views/mixins/#more-than-just-html)
usage of class-based views to render the page in a dynamic website.

```python
import json
from django.http import HttpResponse
from django.views.generic import TemplateView


class JSONResponseMixin(object):
    """
    A mixin that can be used to render a JSON response.
    """
    def render_to_json_response(self, context, **response_kwargs):
        """
        Returns a JSON response, transforming 'context' to make the payload.
        """
        return HttpResponse(
            self.convert_context_to_json(context),
            content_type='application/json',
            **response_kwargs
        )

    def convert_context_to_json(self, context):
        "Convert the context dictionary into a JSON object"
        # Note: This is *EXTREMELY* naive; in reality, you'll need
        # to do much more complex handling to ensure that arbitrary
        # objects -- such as Django model instances or querysets
        # -- can be serialized as JSON.
        return json.dumps(context)


class JSONView(JSONResponseMixin, TemplateView):
    def render_to_response(self, context, **response_kwargs):
        return self.render_to_json_response(context, **response_kwargs)

    def get_context_data(self, **kwargs):
        return {'this-is': 'dummy-data'}
```

The same design pattern can work with django-bakery to build a flat version of
the JSON response. All that's necessary is to substitute a buildable view with some
additional configuration.

```{code-block} python
:emphasize-lines: 3,29-45

import json
from django.http import HttpResponse
from bakery.views import BuildableTemplateView


class JSONResponseMixin(object):
    """
    A mixin that can be used to render a JSON response.
    """
    def render_to_json_response(self, context, **response_kwargs):
        """
        Returns a JSON response, transforming 'context' to make the payload.
        """
        return HttpResponse(
            self.convert_context_to_json(context),
            content_type='application/json',
            **response_kwargs
        )

    def convert_context_to_json(self, context):
        "Convert the context dictionary into a JSON object"
        # Note: This is *EXTREMELY* naive; in reality, you'll need
        # to do much more complex handling to ensure that arbitrary
        # objects -- such as Django model instances or querysets
        # -- can be serialized as JSON.
        return json.dumps(context)


class BuildableJSONView(JSONResponseMixin, BuildableTemplateView):
    # Nothing more than standard bakery configuration here
    build_path = 'jsonview.json'

    def render_to_response(self, context, **response_kwargs):
        return self.render_to_json_response(context, **response_kwargs)

    def get_context_data(self, **kwargs):
        return {'this-is': 'dummy-data'}

    def get_content(self):
        """
        Overrides an internal trick of buildable views so that bakery
        can render the HttpResponse substituted above for the typical Django
        template by the JSONResponseMixin
        """
        return self.get(self.request).content
```

## Building a single view on demand

The `build` management command can regenerate all pages for all views in the
`BAKERY_VIEWS` settings variable. A {doc}`buildable model </buildablemodels>`
can recreate all pages related to a single object. But can you rebuild all pages
created by just one view? Yes, and all it takes is importing the view and invoking
its `build_method`.

```python
>>> from yourapp.views import DummyDe­tailView
>>> DummyDe­tailView().build_method()
```

A simple way to automate that kind of targeted build might be to create a
[custom management command](https://docs.djangoproject.com/en/dev/howto/custom-management-commands/)
and connect it to a [cron job](http://en.wikipedia.org/wiki/Cron).

```python
from django.core.management.base import BaseCommand, CommandError
from yourapp.views import DummyDetailView

class Command(BaseCommand):
    help = 'Rebuilds all pages created by the DummyDetailView'

    def handle(self, *args, **options):
        DummyDe­tailView().build_method()
```

Or, if you wanted to rebuild the view without deleting everything else in the existing
build directory, you could pass it as an argument to the standard `build` command
with instructions to skip everything else it normally does.

```bash
$ python manage.py build yourapp.views.DummyDetailView --keep-build-dir --skip-static --skip-media
```

## Enabling Amazon's accelerated uploads

If your bucket has enabled [Amazon's S3 transfer acceleration service](https://aws.amazon.com/blogs/aws/aws-storage-update-amazon-s3-transfer-acceleration-larger-snowballs-in-more-regions/?sc_channel=sm&sc_campaign=launches_2016&sc_publisher=tw_go&sc_content=chi_summit_s3_transfer_acc&sc_country_video=global&sc_geo=global&sc_category=s3&adbsc=social60723236&adbid=983704521666913&adbpl=fb&adbpr=153063591397681&adbid=983942131643152&adbpl=fb&adbpr=153063591397681),
you can configure bakery it use by overriding the default `AWS_S3_HOST` variable in `settings.py`.

```python
AWS_S3_HOST = 's3-accelerate.amazonaws.com'
```
