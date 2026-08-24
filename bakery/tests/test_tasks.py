import logging
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from bakery import tasks


@pytest.fixture
def task_object():
    content_type = MagicMock()
    obj = MagicMock()
    content_type.get_object_for_this_type.return_value = obj
    return content_type, obj


@pytest.mark.parametrize(
    ("task", "method"),
    [
        pytest.param(tasks.publish_object, "build", id="publish"),
        pytest.param(tasks.unpublish_object, "unbuild", id="unpublish"),
    ],
)
def test_task_processes_object_and_publishes(task, method, task_object):
    content_type, obj = task_object

    with (
        patch.object(
            tasks.ContentType.objects, "get_for_id", return_value=content_type
        ) as get_for_id,
        patch.object(tasks.management, "call_command") as call_command,
    ):
        task.run(101, 202)

    get_for_id.assert_called_once_with(101)
    content_type.get_object_for_this_type.assert_called_once_with(pk=202)
    getattr(obj, method).assert_called_once_with()
    call_command.assert_called_once_with("publish")


@override_settings(ALLOW_BAKERY_AUTO_PUBLISHING=False)
@pytest.mark.parametrize(
    ("task", "method"),
    [
        pytest.param(tasks.publish_object, "build", id="publish"),
        pytest.param(tasks.unpublish_object, "unbuild", id="unpublish"),
    ],
)
def test_task_skips_publishing_when_auto_publishing_is_disabled(
    task, method, task_object, caplog
):
    content_type, obj = task_object

    with (
        caplog.at_level(logging.INFO, logger="bakery.tasks"),
        patch.object(
            tasks.ContentType.objects, "get_for_id", return_value=content_type
        ),
        patch.object(tasks.management, "call_command") as call_command,
    ):
        task.run(101, 202)

    getattr(obj, method).assert_called_once_with()
    call_command.assert_not_called()
    assert any(
        "ALLOW_BAKERY_AUTO_PUBLISHING is False" in message
        for message in caplog.messages
    )


@pytest.mark.parametrize(
    ("task", "method", "task_name"),
    [
        pytest.param(tasks.publish_object, "build", "publish_object", id="publish"),
        pytest.param(
            tasks.unpublish_object, "unbuild", "unpublish_object", id="unpublish"
        ),
    ],
)
def test_task_logs_exceptions_from_object_processing(
    task, method, task_name, task_object, caplog
):
    content_type, obj = task_object
    getattr(obj, method).side_effect = RuntimeError("processing failed")

    with (
        caplog.at_level(logging.ERROR, logger="bakery.tasks"),
        patch.object(
            tasks.ContentType.objects, "get_for_id", return_value=content_type
        ),
        patch.object(tasks.management, "call_command") as call_command,
    ):
        task.run(101, 202)

    call_command.assert_not_called()
    assert f"Task Error: {task_name}" in caplog.messages
