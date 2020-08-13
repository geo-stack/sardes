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
import pandas as pd
from flaky import flaky

# ---- Local imports
from sardes.database.database_manager import DatabaseConnectionManager
from sardes.database.accessor_demo import DatabaseAccessorDemo


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def DATAF():
    return pd.DataFrame([1, 2, 3, 4], columns=['values'])


@pytest.fixture
def dbmanager(qtbot, mocker):
    dbmanager = DatabaseConnectionManager()
    return dbmanager


@pytest.fixture
def dbaccessor(qtbot, mocker, DATAF):
    def get_something():
        sleep(0.5)
        return DATAF.copy()

    def set_something(index, value):
        sleep(0.5)
        DATAF.loc[index, 'values'] = value

    dbaccessor = DatabaseAccessorDemo()
    dbaccessor.get_something = get_something
    dbaccessor.set_something = set_something
    return dbaccessor


# =============================================================================
# ---- Tests
# =============================================================================
def test_dbmanager_init(dbmanager):
    """Test that the databse connection manager is initialized correctly."""
    assert dbmanager


def test_dbmanager_connect(dbmanager, dbaccessor, qtbot):
    """
    Test that the database connection manager connection to the database is
    working as expected.
    """
    # We ask the manager to connect to the database.
    assert not dbmanager.is_connected()
    with qtbot.waitSignal(dbmanager.sig_database_connection_changed,
                          timeout=1500):
        dbmanager.connect_to_db(dbaccessor)
        assert len(dbmanager._queued_tasks) == 0
        assert len(dbmanager._pending_tasks) == 0
        assert len(dbmanager._running_tasks) == 1
        assert dbmanager.is_connecting()
    assert dbmanager.is_connected()

    # We ask the manager to close the connection with the database.
    with qtbot.waitSignal(dbmanager.sig_database_connection_changed,
                          timeout=1500):
        dbmanager.disconnect_from_db()
        assert len(dbmanager._queued_tasks) == 0
        assert len(dbmanager._pending_tasks) == 0
        assert len(dbmanager._running_tasks) == 1
    assert not dbmanager.is_connected()
    assert len(dbmanager._running_tasks) == 0

    qtbot.waitUntil(lambda: not dbmanager._db_connection_thread.isRunning())


@flaky(max_runs=3)
def test_run_tasks_if_posponed(dbmanager, dbaccessor, qtbot):
    """
    Test that the database manager is managing the queued as expected
    when the execution is postponed.
    """
    with qtbot.waitSignal(dbmanager.sig_database_connection_changed,
                          timeout=1500):
        dbmanager.connect_to_db(dbaccessor)

    returned_values = []

    def task_callback(dataf):
        returned_values.append(dataf)

    # We send the task to the manager, but we ask to pospone the execution
    # of each task so that they can be executed by the worker all at once.
    dbmanager.get('something', callback=task_callback, postpone_exec=True)
    dbmanager.get('something', callback=task_callback, postpone_exec=True)
    dbmanager.set('something', 2, -19.5, postpone_exec=True)
    dbmanager.get('something', callback=task_callback, postpone_exec=True)

    assert len(dbmanager._queued_tasks) == 4
    assert len(dbmanager._pending_tasks) == 0
    assert len(dbmanager._running_tasks) == 0
    assert returned_values == []

    # We ask the manager to execute the queued tasks in a single run.
    with qtbot.waitSignal(dbmanager.sig_run_tasks_finished, timeout=5000):
        dbmanager.run_tasks()
        assert len(dbmanager._queued_tasks) == 0
        assert len(dbmanager._pending_tasks) == 0
        assert len(dbmanager._running_tasks) == 4

    assert len(dbmanager._running_tasks) == 0
    assert len(returned_values) == 3
    assert returned_values[0]['values'].values.tolist() == [1, 2, 3, 4]
    assert returned_values[1]['values'].values.tolist() == [1, 2, 3, 4]
    assert returned_values[2]['values'].values.tolist() == [1, 2, -19.5, 4]

    qtbot.waitUntil(lambda: not dbmanager._db_connection_thread.isRunning())


def test_run_tasks_if_busy(dbmanager, dbaccessor, qtbot):
    """
    Test that the database manager is managing the queued as expected
    when adding new tasks while the worker is busy.
    """
    with qtbot.waitSignal(dbmanager.sig_database_connection_changed,
                          timeout=1500):
        dbmanager.connect_to_db(dbaccessor)

    returned_values = []

    def task_callback(dataf):
        returned_values.append(dataf)

    # We send the task to the manager, but we ask to pospone the execution
    # of each task so that they can be executed by the worker all at once.
    dbmanager.get('something', callback=task_callback, postpone_exec=True)
    dbmanager.get('something', callback=task_callback, postpone_exec=True)
    dbmanager.set('something', 2, -19.5, postpone_exec=True)
    assert len(dbmanager._queued_tasks) == 3
    assert len(dbmanager._pending_tasks) == 0
    assert len(dbmanager._running_tasks) == 0

    # Then we ask the manager to start executing the tasks, but we then
    # send another task to execute while the worker is busy.
    dbmanager.run_tasks()
    assert len(dbmanager._queued_tasks) == 0
    assert len(dbmanager._pending_tasks) == 0
    assert len(dbmanager._running_tasks) == 3
    assert dbmanager._db_connection_thread.isRunning()

    # While the worker is running, we send another task, but postpone its
    # execution.
    dbmanager.set('something', 1, 0.512, postpone_exec=True)
    assert len(dbmanager._queued_tasks) == 1
    assert len(dbmanager._pending_tasks) == 0
    assert len(dbmanager._running_tasks) == 3
    assert dbmanager._db_connection_thread.isRunning()

    # While the worker is still running, we send another task, but do not
    # postpone its execution. This should cause this task and the previous
    # one to be moved as pending tasks.
    dbmanager.get('something', callback=task_callback, postpone_exec=False)
    assert len(dbmanager._queued_tasks) == 0
    assert len(dbmanager._pending_tasks) == 2
    assert len(dbmanager._running_tasks) == 3

    qtbot.waitUntil(lambda: len(dbmanager._pending_tasks) == 0, timeout=3000)

    # Once the first stack of tasks is executed, the additional 2 other tasks
    # should be executed automatically.
    assert dbmanager._db_connection_thread.isRunning()
    assert len(dbmanager._queued_tasks) == 0
    assert len(dbmanager._pending_tasks) == 0
    assert len(dbmanager._running_tasks) == 2

    assert len(returned_values) == 2
    assert returned_values[0]['values'].values.tolist() == [1, 2, 3, 4]
    assert returned_values[1]['values'].values.tolist() == [1, 2, 3, 4]

    # We now wait for the worker to finish and assert that all tasks have
    # been executed as expected.
    qtbot.waitSignal(dbmanager.sig_run_tasks_finished)
    qtbot.waitUntil(lambda: not dbmanager._db_connection_thread.isRunning(),
                    timeout=3000)

    assert len(dbmanager._queued_tasks) == 0
    assert len(dbmanager._pending_tasks) == 0
    assert len(dbmanager._running_tasks) == 0

    assert len(returned_values) == 3
    assert returned_values[0]['values'].values.tolist() == [1, 2, 3, 4]
    assert returned_values[1]['values'].values.tolist() == [1, 2, 3, 4]
    assert returned_values[2]['values'].values.tolist() == [1, 0.512, -19.5, 4]


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
