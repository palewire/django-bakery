"""
Models that inherit from Django's default and add methods to make it
convenient for building out flat files.

The magic relies on your view being class-based and having a build_object
method, like the BuildableDetailView included in this app.
"""

from django.db import models, transaction

from bakery.apps import logger


class BuildableModel(models.Model):
    """
    An abstract base model for an object that builds out
    its own detail pages.

    Set `detail_views` to an iterable containing
    strings which represent your class-based
    view (which should inherit from BuildableDetailView),
    then fill out _build_related and _build_extra if need be.
    """

    detail_views = []

    def _get_view(self, name):
        try:
            from django.urls import get_callable
        except ImportError:  # Starting with Django 2.0, django.core.urlresolvers does not
            # exist anymore
            from django.urls import get_callable
        return get_callable(name)

    def _build_related(self):
        """
        Builds related content, such as an RSS feed.
        """
        pass

    def _build_extra(self):
        """
        Build extra content, like copying an image to a thumbnails folder under
        the media folder.
        """
        pass

    def _unbuild_extra(self):
        """
        Remove extra content, like deleting an image from a thumbnails folder
        under the media folder.
        """
        pass

    def build(self):
        """
        Iterates through the views pointed to by self.detail_views, runs
        build_object with `self`, and calls _build_extra()
        and _build_related().
        """
        logger.debug(f"BuildableModel.build() called for {self.__class__.__name__}: {self}")
        if hasattr(self, "detail_views") and self.detail_views:
            from django.utils.module_loading import import_string

            # from bakery.views.base import BuildableMixin # Should be
            # imported at module level if used for issubclass

            for view_str in self.detail_views:
                logger.debug(f"[BuildableModel.build] Processing view_str: {view_str}")
                try:
                    view_klass = import_string(view_str)
                    logger.debug(
                        f"[BuildableModel.build] Imported view_klass: "
                        f"{view_klass}, type: {type(view_klass)}",
                    )

                    if not callable(view_klass):  # Explicit check
                        logger.error(
                            f"[BuildableModel.build] {view_str} ("
                            f"{view_klass}) is not callable. Skipping.",
                        )
                        continue

                    # Ensure BuildableMixin is in scope for issubclass check if you re-enable it
                    # from bakery.views.base import BuildableMixin
                    # if not issubclass(view_klass, BuildableMixin):
                    #     logger.warning(f"View {view_str} for {self} is not
                    #     a BuildableMixin subclass. Skipping.")
                    #     continue

                    logger.debug(f"[BuildableModel.build] Instantiating {view_klass}")
                    view_instance = view_klass()
                    logger.debug(
                        f"[BuildableModel.build] Instantiated view_instance: "
                        f"{view_instance}, type: {type(view_instance)}",
                    )

                    if hasattr(view_instance, "build_object") and callable(
                        view_instance.build_object,
                    ):
                        logger.debug(
                            f"[BuildableModel.build] Calling build_object on {view_str} for {self}",
                        )
                        view_instance.build_object(self)
                    else:
                        logger.warning(
                            f"View {view_str} for {self} has no callable 'build_object' method. "
                            "Attempting generic view_instance.build() if available.",
                        )
                        if hasattr(view_instance, "build") and callable(view_instance.build):
                            logger.debug(
                                f"[BuildableModel.build] Calling generic "
                                f"build() on {view_str} for {self}",
                            )
                            view_instance.build()
                        else:
                            logger.error(
                                f"No suitable build method found on {view_str} for {self}.",
                            )

                except ImportError:
                    logger.error(
                        f"Could not import detail view: {view_str} for {self}",
                        exc_info=True,
                    )
                except TypeError as te:  # Catch TypeError specifically
                    logger.error(
                        f"TypeError during processing of view {view_str} for {self}: {te}",
                        exc_info=True,
                    )
                    # Log details about what might have been a module
                    if "module" in str(te).lower() and "not callable" in str(te).lower():
                        view_klass = (
                            view_klass if "view_klass" in locals() else "view_klass not defined."
                        )
                        logger.error(f"Object that was attempted to be called: {view_klass}")
                except Exception as e:
                    logger.error(
                        f"Generic error building detail view {view_str} for {self}: {e}",
                        exc_info=True,
                    )
        else:
            logger.debug(
                f"No detail_views specified for {self}. Model build() does nothing further.",
            )

    def unbuild(self):
        """
        Iterates through the views pointed to by self.detail_views, runs
        unbuild_object with `self`, and calls _build_extra()
        and _build_related().
        """
        for detail_view in self.detail_views:
            view = self._get_view(detail_view)
            view().unbuild_object(self)
        self._unbuild_extra()
        # _build_related again to kill the object from RSS etc.
        self._build_related()

    def get_absolute_url(self):
        """
        Returns the absolute URL for this object.

        This method should be implemented by subclasses to provide the
        correct URL for accessing the detail page of the object.

        If the superclass has a get_absolute_url method, it will be called.
        Otherwise, an AttributeError will be raised, indicating that the
        method is not implemented.
        """
        if hasattr(super(), "get_absolute_url"):
            return super().get_absolute_url()
        raise AttributeError(
            f"{self.__clas__.__name__} object  does not define a "
            f"get_absolute_url method or is not implemented in its hierarchy",
        )

    class Meta:
        abstract = True


class AutoPublishingBuildableModel(BuildableModel):
    """
    Integrates with Celery tasks to automatically publish or unpublish
    objects when they are saved.

    This is done using an override on the save method that inspects
    if the object ought to be published, republished or unpublished.

    Requires an indicator of whether the object should been
    published or unpublished. By default it looks to a BooleanField
    called ``is_published`` for the answer, but other methods could
    be employed by overriding the ``get_publication_status`` method.
    """

    # The name of the field that this model will inspect to determine
    # the object's publication status by default.
    publication_status_field = "is_published"

    def get_publication_status(self):
        """
        Returns a boolean (True or False) indicating whether the object
        is "live" and ought to be published or not.

        Used to determine whether the save method should seek to publish,
        republish or unpublish the object when it is saved.

        By default, it looks for a BooleanField with the name defined in
        the model's 'publication_status_field'.

        If your model uses a CHOICES list of strings or other more complex
        means to indicate publication status you need to override this method
        and have it negotiate your object to return either True or False.
        """
        return getattr(self, self.publication_status_field)

    def save(self, *args, **kwargs):
        """
        A custom save that publishes or unpublishes the object where
        appropriate.

        Save with keyword argument obj.save(publish=False) to skip the process.
        """
        from django.contrib.contenttypes.models import ContentType

        from bakery import tasks

        # if obj.save(publish=False) has been passed, we skip everything.
        if not kwargs.pop("publish", True):
            super().save(*args, **kwargs)
        # Otherwise, for the standard obj.save(), here we go...
        else:
            # First figure out if the record is an addition, or an edit of
            # a preexisting record.
            try:
                preexisting = self.__class__.objects.get(pk=self.pk)
            except self.__class__.DoesNotExist:
                preexisting = None
            # If this is an addition...
            if not preexisting:
                # We will publish if that's the boolean
                if self.get_publication_status():
                    action = "publish"
                # Otherwise we will do nothing do nothing
                else:
                    action = None
            # If this is an edit...
            else:
                # If it's being unpublished...
                if not self.get_publication_status() and preexisting.get_publication_status():
                    action = "unpublish"
                # If it's being published...
                elif self.get_publication_status():
                    action = "publish"
                # If it's remaining unpublished...
                else:
                    action = None
            # Now, no matter what, save it normally inside of a dedicated
            # database transaction so that we are sure that the save will
            # be complete before we trigger any task
            with transaction.atomic():
                super().save(*args, **kwargs)
            # Finally, depending on the action, fire off a task
            ct = ContentType.objects.get_for_model(self.__class__)
            if action == "publish":
                tasks.publish_object.delay(ct.pk, self.pk)
            elif action == "unpublish":
                tasks.unpublish_object.delay(ct.pk, self.pk)

    def delete(self, *args, **kwargs):
        """
        Triggers a task that will unpublish the object after it is deleted.

        Save with keyword argument obj.delete(unpublish=False) to skip it.
        """
        from django.contrib.contenttypes.models import ContentType

        from bakery import tasks

        # if obj.save(unpublish=False) has been passed, we skip the task.
        unpublish = kwargs.pop("unpublish", True)
        # Delete it from the database
        super().delete(*args, **kwargs)
        if unpublish:
            ct = ContentType.objects.get_for_model(self.__class__)
            tasks.unpublish_object.delay(ct.pk, self.pk)

    class Meta:
        abstract = True
