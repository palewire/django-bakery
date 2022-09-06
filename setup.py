import os
import tempfile
from setuptools import setup
from distutils.core import Command


def read(file_name):
    """Read in the supplied file name from the root directory.
    Args:
        file_name (str): the name of the file
    Returns: the content of the file
    """
    this_dir = os.path.dirname(__file__)
    file_path = os.path.join(this_dir, file_name)
    with open(file_path) as f:
        return f.read()


def version_scheme(version):
    """Version scheme hack for setuptools_scm.
    Appears to be necessary to due to the bug documented here: https://github.com/pypa/setuptools_scm/issues/342
    If that issue is resolved, this method can be removed.
    """
    import time

    from setuptools_scm.version import guess_next_version

    if version.exact:
        return version.format_with("{tag}")
    else:
        _super_value = version.format_next_version(guess_next_version)
        now = int(time.time())
        return _super_value + str(now)


def local_version(version):
    """Local version scheme hack for setuptools_scm.
    Appears to be necessary to due to the bug documented here: https://github.com/pypa/setuptools_scm/issues/342
    If that issue is resolved, this method can be removed.
    """
    return ""


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
            AWS_REGION='us-west-1',
            # Celery configuration
            BROKER_URL = 'django://',
        )
        import django
        django.setup()
        from django.core.management import call_command
        call_command('test', 'bakery.tests', verbosity=3)


setup(
    name='django-bakery',
    description='A set of helpers for baking your Django site out as flat files',
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    author='Ben Welsh',
    author_email='b@palewi.re',
    url='http://www.github.com/palewire/django-bakery/',
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
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Framework :: Django',
        'Framework :: Django :: 2',
        'Framework :: Django :: 3',
        'Framework :: Django :: 4',
        'License :: OSI Approved :: MIT License',
    ],
    install_requires=[
        'six>1.5.2',
        'boto3>=1.4.4',
        'fs>=2.0.17',
    ],
    cmdclass={'test': TestCommand},
    setup_requires=["setuptools_scm"],
    use_scm_version={"version_scheme": version_scheme, "local_scheme": local_version},
)
