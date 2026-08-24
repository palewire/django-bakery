from django.core.management.commands import runserver
from django.test.utils import override_settings


class Command(runserver.Command):
    help = "Starts a variation of Django's runserver designed to serve \
the static files you've built."

    @override_settings(ROOT_URLCONF="bakery.static_urls")
    def handle(self, *args: object, **kwds: object) -> object:
        runserver.Command.handle(self, *args, **kwds)
