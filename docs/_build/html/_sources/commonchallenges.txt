Common challenges
=================

Building JSON instead of HTML
-----------------------------

Suppose you have a view the acts like an API, generating a small snippet
of JSON. In this case,
`the official Django documentation recommends the following <https://docs.djangoproject.com/en/1.6/topics/class-based-views/mixins/#more-than-just-html>`_
usage of class-based views to render the page in a dynamic website.

.. code-block:: python

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


The same design pattern can work with django-bakery to build a flat version of 
the JSON response. All that's necessary is to substitute a buildable view with some
additional configuration.

.. code-block:: python
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

Building a single view on demand
--------------------------------

The ``build`` management command can regenerate all pages for all views in the
``BAKERY_VIEWS`` settings variable. A :doc:`buildable model </buildablemodels>`
can recreate all pages related to a single object. But can you rebuild all pages
created by just one view? Yes, and all it takes is importing the view and invoking
its ``build_method``.

.. code-block:: python

    >>> from yourapp.views import DummyDe­tailView
    >>> DummyDe­tailView().build_method()

A simple way to automate that kind of targeted build might be to create a 
`custom management command <https://docs.djangoproject.com/en/dev/howto/custom-management-commands/>`_
and connect it to a `cron job <http://en.wikipedia.org/wiki/Cron>`_.

.. code-block:: python

    from django.core.management.base import BaseCommand, CommandError
    from yourapp.views import DummyDetailView

    class Command(BaseCommand):
        help = 'Rebuilds all pages created by the DummyDetailView'

        def handle(self, *args, **options):
            DummyDe­tailView().build_method()

Or, if you wanted to rebuild the view without deleting everything else in the existing
build directory, you could pass it as an argument to the standard ``build`` command
with instructions to skip everything else it normally does.

.. code-block:: bash

    $ python manage.py build yourapp.views.DummyDetailView --keep-build-dir --skip-static --skip-media


