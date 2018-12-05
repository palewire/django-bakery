import os
import tempfile
from setuptools import setup
from distutils.core import Command


class TestCommand(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        from django.conf import settings
        settings.configure(
            DATABASES={
                'default': {
                    'NAME': 'test.db',
                    'TEST_NAME': 'test.db',
                    'ENGINE': 'django.db.backends.sqlite3'
                }
            },
            INSTALLED_APPS = (
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'django.contrib.staticfiles',
                'bakery',
            ),
            MIDDLEWARE_CLASSES=(),
            TEMPLATES = [
                {
                    'BACKEND': 'django.template.backends.django.DjangoTemplates',
                    'DIRS': [os.path.abspath(
                         os.path.join(
                             os.path.dirname(__file__),
                             'bakery',
                             'tests',
                             'templates',
                         ),
                    )],
                    'APP_DIRS': True,
                    'OPTIONS': {
                        'context_processors': [],
                    },
                },
            ],
            BUILD_DIR = tempfile.mkdtemp(),
            STATIC_ROOT = os.path.abspath(
                 os.path.join(
                     os.path.dirname(__file__),
                     'bakery',
                     'tests',
                     'static',
                 ),
            ),
            STATIC_URL = '/static/',
            MEDIA_ROOT = os.path.abspath(
                 os.path.join(
                     os.path.dirname(__file__),
                     'bakery',
                     'tests',
                     'media',
                 ),
            ),
            MEDIA_URL = '/media/',
            BAKERY_VIEWS = ('bakery.tests.MockDetailView',),
            # The publish management command needs these to exit, but
            # we're mocking boto, so we can put nonesense in here
            AWS_ACCESS_KEY_ID = 'MOCK_ACCESS_KEY_ID',
            AWS_SECRET_ACCESS_KEY = 'MOCK_SECRET_ACCESS_KEY',
            AWS_BUCKET_NAME = 'mock_bucket',
            # Celery configuration
            BROKER_URL = 'django://',
        )
        import django
        django.setup()
        from django.core.management import call_command
        call_command('test', 'bakery.tests', verbosity=3)


setup(
    name='django-bakery',
    version='0.12.7',
    description='A set of helpers for baking your Django site out as flat files',
    author='The Los Angeles Times Data Desk',
    author_email='datadesk@latimes.com',
    url='http://www.github.com/datadesk/django-bakery/',
    license="MIT",
    packages=(
        'bakery',
        'bakery.views',
        'bakery.management',
        'bakery.management.commands',
        'bakery.tests',
        'bakery.tests.static',
        'bakery.tests.media',
        'bakery.tests.templates',
    ),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Framework :: Django',
        'Framework :: Django :: 1.11',
        'Framework :: Django :: 2.0',
        'Framework :: Django :: 2.1',
        'License :: OSI Approved :: MIT License',
    ],
    install_requires=[
        'six>1.5.2',
        'boto3>=1.4.4',
        'fs>=2.0.17',
    ],
    cmdclass={'test': TestCommand}
)
