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
from time import sleep

# ---- Third party imports
import pytest
import pandas as pd

# ---- Local imports
from sardes.database.database_manager import DatabaseConnectionManager
from sardes.api.database_accessor import DatabaseAccessorBase


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def DATAF():
    return pd.DataFrame([1, 2, 3, 4], columns=['values'])


@pytest.fixture
def dbmanager(qtbot, mocker):
    dbmanager = DatabaseConnectionManager()
    yield dbmanager

    qtbot.waitUntil(lambda: not dbmanager._thread.isRunning())


@pytest.fixture
def dbaccessor(qtbot, mocker, DATAF):
    class DatabaseAccessorMock(DatabaseAccessorBase):

        def _connect(self):
            connection = True
            connection_error = None
            return connection, connection_error

        def is_connected(self):
            return self._connection is True

        def commit_transaction(self):
            # This accessor does not support journal logging.
            pass

        def begin_transaction(self):
            # This accessor does not support journal logging.
            pass

        def close_connection(self):
            self._connection = None

        def _get_something(self):
            sleep(0.5)
            return DATAF.copy()

        def _set_something(self, index, value):
            sleep(0.5)
            DATAF.loc[index, 'values'] = value

    dbaccessor = DatabaseAccessorMock()
    return dbaccessor


# =============================================================================
# ---- Tests
# =============================================================================
def test_connect_to_database(dbmanager, dbaccessor, qtbot):
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


def test_get_and_set_in_database(dbmanager, dbaccessor, qtbot):
    """
    Test that the database manager is managing get and set tasks as expected.
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


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
