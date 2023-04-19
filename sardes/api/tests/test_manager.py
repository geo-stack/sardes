# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the TaskManagerBase class.
"""

# ---- Standard imports
from time import sleep

# ---- Third party imports
import pytest
import pandas as pd

# ---- Local imports
from sardes.api.taskmanagers import WorkerBase, TaskManagerBase


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def DATAF():
    return pd.DataFrame([1, 2, 3, 4], columns=['values'])


@pytest.fixture
def worker(DATAF):
    def _get_something():
        sleep(0.5)
        return DATAF.copy(),

    def _set_something(index, value):
        sleep(0.5)
        DATAF.loc[index, 'values'] = value

    worker = WorkerBase()
    worker._get_something = _get_something
    worker._set_something = _set_something
    return worker


@pytest.fixture
def task_manager(worker, qtbot):
    task_manager = TaskManagerBase()
    task_manager.set_worker(worker)
    yield task_manager

    # We wait for the manager's thread to fully stop to avoid segfault error.
    qtbot.waitUntil(lambda: not task_manager._thread.isRunning())


# =============================================================================
# ---- Tests
# =============================================================================
def test_run_tasks(task_manager, qtbot):
    """
    Test that the task manager is managing queued tasks as expected.
    """
    returned_values = []

    def task_callback(dataf):
        returned_values.append(dataf)

    # Add some tasks to the manager.
    task_manager.add_task('get_something', task_callback)
    task_manager.add_task('get_something', task_callback)
    task_manager.add_task('set_something', None, 2, -19.5)
    task_manager.add_task('get_something', task_callback)

    assert len(task_manager._queued_tasks) == 4
    assert len(task_manager._pending_tasks) == 0
    assert len(task_manager._running_tasks) == 0
    assert returned_values == []

    # We then ask the manager to execute the queued tasks.
    with qtbot.waitSignal(task_manager.sig_run_tasks_finished, timeout=5000):
        task_manager.run_tasks()

        # Assert that all queued tasks are now running tasks.
        assert len(task_manager._queued_tasks) == 0
        assert len(task_manager._pending_tasks) == 0
        assert len(task_manager._running_tasks) == 4

    assert len(task_manager._running_tasks) == 0
    assert len(returned_values) == 3
    assert returned_values[0]['values'].values.tolist() == [1, 2, 3, 4]
    assert returned_values[1]['values'].values.tolist() == [1, 2, 3, 4]
    assert returned_values[2]['values'].values.tolist() == [1, 2, -19.5, 4]


def test_run_tasks_if_busy(task_manager, qtbot):
    """
    Test that the manager is managing the queued tasks as expected
    when adding new tasks while the worker is busy.
    """
    returned_values = []

    def task_callback(dataf):
        returned_values.append(dataf)

    # Add some tasks to the manager.
    task_manager.add_task('get_something', task_callback)
    task_manager.add_task('get_something', task_callback)
    task_manager.add_task('set_something', None, 2, -19.5)
    assert len(task_manager._queued_tasks) == 3
    assert len(task_manager._pending_tasks) == 0
    assert len(task_manager._running_tasks) == 0

    # We then ask the manager to execute the queued tasks.
    with qtbot.waitSignal(task_manager.sig_run_tasks_finished, timeout=5000):
        task_manager.run_tasks()

        # Assert that all queued tasks are now running tasks.
        assert len(task_manager._queued_tasks) == 0
        assert len(task_manager._pending_tasks) == 0
        assert len(task_manager._running_tasks) == 3
        assert task_manager._thread.isRunning()

        # While the worker is running, we add two other tasks to the manager.
        task_manager.add_task('set_something', None, 1, 0.512)
        task_manager.add_task('get_something', task_callback)
        assert len(task_manager._queued_tasks) == 2
        assert len(task_manager._pending_tasks) == 0
        assert len(task_manager._running_tasks) == 3
        assert task_manager._thread.isRunning()

        # We then ask the manager to execute the tasks that we just added.
        # These additional tasks should be run automatically after the first
        # stack of tasks have been executed.
        task_manager.run_tasks()
        assert len(task_manager._queued_tasks) == 0
        assert len(task_manager._pending_tasks) == 2
        assert len(task_manager._running_tasks) == 3
        assert task_manager._thread.isRunning()

    # We then assert that all tasks have been executed as expected.
    assert len(task_manager._queued_tasks) == 0
    assert len(task_manager._pending_tasks) == 0
    assert len(task_manager._running_tasks) == 0

    assert len(returned_values) == 3
    assert returned_values[0]['values'].values.tolist() == [1, 2, 3, 4]
    assert returned_values[1]['values'].values.tolist() == [1, 2, 3, 4]
    assert returned_values[2]['values'].values.tolist() == [1, 0.512, -19.5, 4]


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
