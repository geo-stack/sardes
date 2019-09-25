# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the DatabaseConnectionManager class.
"""

# ---- Standard imports
import os.path as osp
from time import sleep

# ---- Third party imports
import pytest

# ---- Local imports
from sardes.database.database_manager import DatabaseConnectionManager
from sardes.database.accessor_demo import DatabaseAccessorDemo


def _do_something(some_value):
    sleep(0.3)
    return some_value,


class DatabaseConnectionManagerMock(DatabaseConnectionManager):
    def do_something(self, some_value, callback=None, postpone_exec=False):
        self._data_changed = True
        self._add_task('do_something', callback, some_value)
        if not postpone_exec:
            self.run_tasks()


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dbmanager(qtbot, mocker):
    dbmanager = DatabaseConnectionManagerMock()
    dbmanager._db_connection_worker._do_something = _do_something
    return dbmanager


@pytest.fixture
def dbaccessor(qtbot, mocker):
    dbaccessor = DatabaseAccessorDemo()
    return dbaccessor


# =============================================================================
# ---- Tests
# =============================================================================
def test_dbmanager_init(dbmanager):
    """Test that the databse connection manager is initialized correctly."""
    assert dbmanager


def test_dbmanager_connect(dbmanager, dbaccessor, qtbot):
    """
    Test that the databse connection manager connection to the database is
    working as expected.
    """
    # We ask the manager to connect to the database.
    assert not dbmanager.is_connected()
    with qtbot.waitSignal(dbmanager.sig_database_connection_changed,
                          timeout=3000):
        dbmanager.connect_to_db(dbaccessor)
        assert len(dbmanager._queued_tasks) == 0
        assert len(dbmanager._pending_tasks) == 0
        assert len(dbmanager._running_tasks) == 1
        assert dbmanager.is_connecting()
    assert dbmanager.is_connected()

    # We ask the manager to close the connection with the database.
    with qtbot.waitSignal(dbmanager.sig_database_connection_changed,
                          timeout=3000):
        dbmanager.disconnect_from_db()
        assert len(dbmanager._queued_tasks) == 0
        assert len(dbmanager._pending_tasks) == 0
        assert len(dbmanager._running_tasks) == 1
    assert not dbmanager.is_connected()
    assert len(dbmanager._running_tasks) == 0


def test_run_tasks_if_posponed(dbmanager, dbaccessor, qtbot):
    """
    Test that the database manager is managing the queued as expected
    when the execution is postponed.
    """
    expected_values = [1, 2, 3]
    returned_values = []

    def task_callback(value):
        returned_values.append(value)

    # We send the task to the manager, but we ask to pospone the execution
    # of each task so that they can be executed by the worker all at once.
    for value in expected_values:
        dbmanager.do_something(value, task_callback, postpone_exec=True)

    assert len(dbmanager._queued_tasks) == len(expected_values)
    assert len(dbmanager._pending_tasks) == 0
    assert len(dbmanager._running_tasks) == 0
    assert returned_values == []

    # We ask the manager to execute the queued tasks in a single run.
    with qtbot.waitSignal(dbmanager.sig_database_data_changed, timeout=3000):
        dbmanager.run_tasks()
        assert len(dbmanager._queued_tasks) == 0
        assert len(dbmanager._pending_tasks) == 0
        assert len(dbmanager._running_tasks) == len(expected_values)

    assert len(dbmanager._running_tasks) == 0
    assert returned_values == expected_values


def test_run_tasks_if_busy(dbmanager, dbaccessor, qtbot):
    """
    Test that the database manager is managing the queued as expected
    when adding new tasks while the worker is busy.
    """
    returned_values = []

    def task_callback(value):
        returned_values.append(value)

    # We send the task to the manager, but we ask to pospone the execution
    # of each task so that they can be executed by the worker all at once.
    dbmanager.do_something(1, task_callback, postpone_exec=True)
    dbmanager.do_something(2, task_callback, postpone_exec=True)
    dbmanager.do_something(3, task_callback, postpone_exec=True)
    assert len(dbmanager._queued_tasks) == 3
    assert len(dbmanager._pending_tasks) == 0
    assert len(dbmanager._running_tasks) == 0

    # Then we ask the manager to start executing the tasks, but we then
    # send another task to execute while the worker is busy.
    with qtbot.waitSignal(dbmanager.sig_database_data_changed, timeout=3000):
        dbmanager.run_tasks()
        assert len(dbmanager._queued_tasks) == 0
        assert len(dbmanager._pending_tasks) == 0
        assert len(dbmanager._running_tasks) == 3
        assert dbmanager._db_connection_thread.isRunning()

        # While the worker is running, we send another task, but pospone its
        # execution.
        dbmanager.do_something(4, task_callback, postpone_exec=True)
        assert len(dbmanager._queued_tasks) == 1
        assert len(dbmanager._pending_tasks) == 0
        assert len(dbmanager._running_tasks) == 3
        assert dbmanager._db_connection_thread.isRunning()

        # While the worker is still running, we send another task, but do not
        # pospone its execution. This should cause this task and the previous
        # one to be moved as pending tasks.
        dbmanager.do_something(5, task_callback, postpone_exec=False)
        assert len(dbmanager._queued_tasks) == 0
        assert len(dbmanager._pending_tasks) == 2
        assert len(dbmanager._running_tasks) == 3

    # Once the first stack of tasks is executed, the additional 2 other tasks
    # should be executed automatically.
    assert dbmanager._db_connection_thread.isRunning()
    assert len(dbmanager._queued_tasks) == 0
    assert len(dbmanager._pending_tasks) == 0
    assert len(dbmanager._running_tasks) == 2

    # We now wait for the worker to finish and assert that all tasks have
    # been executed as expected.
    qtbot.waitUntil(lambda: not dbmanager._db_connection_thread.isRunning(),
                    timeout=3000)
    assert len(dbmanager._queued_tasks) == 0
    assert len(dbmanager._pending_tasks) == 0
    assert len(dbmanager._running_tasks) == 0

    assert returned_values == [1, 2, 3, 4, 5]


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
