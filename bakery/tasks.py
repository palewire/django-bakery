import logging
from django.conf import settings
from django.core import management
from django.contrib.contenttypes.models import ContentType
logger = logging.getLogger(__name__)
try:
    from celery import shared_task
except ImportError:
    raise ImportError("celery must be installed to use django-bakery's tasks")


@shared_task()
def publish_object(content_type_pk, obj_pk):
    """
    Build all views related to an object, and then sync with S3.

    Accepts primary keys to retrieve a model object that
    inherits bakery's BuildableModel class.
    """
    ct = ContentType.objects.get_for_id(content_type_pk)
    obj = ct.get_object_for_this_type(pk=obj_pk)
    try:
        # Build the object
        logger.info("publish_object task has received %s" % obj)
        obj.build()
        # Run the `publish` management command unless the
        # ALLOW_BAKERY_AUTO_PUBLISHING variable is explictly set to False.
        if not getattr(settings, 'ALLOW_BAKERY_AUTO_PUBLISHING', True):
            logger.info("Not running publish command because \
ALLOW_BAKERY_AUTO_PUBLISHING is False")
        else:
            management.call_command("publish")
    except Exception:
        # Log the error if this crashes
        logger.error("Task Error: publish_object", exc_info=True)


@shared_task()
def unpublish_object(content_type_pk, obj_pk):
    """
    Unbuild all views related to a object and then sync to S3.

    Accepts primary keys to retrieve a model object that
    inherits bakery's BuildableModel class.
    """
    ct = ContentType.objects.get_for_id(content_type_pk)
    obj = ct.get_object_for_this_type(pk=obj_pk)
    try:
        # Unbuild the object
        logger.info("unpublish_object task has received %s" % obj)
        obj.unbuild()
        # Run the `publish` management command unless the
        # ALLOW_BAKERY_AUTO_PUBLISHING variable is explictly set to False.
        if not getattr(settings, 'ALLOW_BAKERY_AUTO_PUBLISHING', True):
            logger.info("Not running publish command because \
ALLOW_BAKERY_AUTO_PUBLISHING is False")
        else:
            management.call_command("publish")
    except Exception:
        # Log the error if this crashes
        logger.error("Task Error: unpublish_object", exc_info=True)
