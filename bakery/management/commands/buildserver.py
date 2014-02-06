from django.test.utils import override_settings
from django.core.management.commands import runserver


class Command(runserver.Command):
    help = "Starts a variation of Django's runserver designed to serve \
the static files you've built."

    @override_settings(ROOT_URLCONF='bakery.static_urls')
    def handle(self, *args, **kwds):
        runserver.Command.handle(self, *args, **kwds)
