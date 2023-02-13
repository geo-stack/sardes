# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the DatabaseConnectionWidget.
"""

# ---- Standard imports
import os
from unittest.mock import Mock
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
from sqlalchemy.exc import OperationalError
import pytest
from qtpy.QtCore import Qt

# ---- Local imports
from sardes.database.database_manager import DatabaseConnectionManager
from sardes.plugins.databases.widgets import DatabaseConnectionWidget
from sardes.widgets.statusbar import ProcessStatusBar
from sardes.api.database_dialog import DatabaseConnectDialogBase
from sardes.api.database_accessor import DatabaseAccessorBase
from sardes.database.accessors.accessor_errors import (
    DatabaseVersionError, DatabaseUpdateError)


# =============================================================================
# ---- Fixtures
# =============================================================================
class DatabaseAccessorMock(DatabaseAccessorBase):
    dbconnection = None
    dbconnection_error = None

    def version(self):
        return 2

    def req_version(self):
        return 3

    def update_database(self):
        pass

    def _connect(self):
        pass

    def is_connected(self):
        return self._connection is not None

    def close_connection(self):
        self._connection = None


class DatabaseConnectDialogMock(DatabaseConnectDialogBase):
    __DatabaseAccessor__ = DatabaseAccessorMock
    __database_type_name__ = 'test_connection'
    __database_type_desc__ = 'An accessor to test the connection logic.'


@pytest.fixture
def dbconnwidget(qtbot, mocker):
    dbconnwidget = DatabaseConnectionWidget(DatabaseConnectionManager())

    # Add a database connection dialog to the database connection widget.
    database_dialog = DatabaseConnectDialogMock()
    dbconnwidget.add_database_dialog(database_dialog)

    qtbot.addWidget(dbconnwidget)
    dbconnwidget.show()
    return dbconnwidget


# =============================================================================
# ---- Tests for DatabaseConnectionWidget
# =============================================================================
def test_dbconnwidget_init(dbconnwidget):
    """Test that the databse connection manager is initialized correctly."""
    assert dbconnwidget
    assert dbconnwidget.status_bar.status == ProcessStatusBar.HIDDEN

    assert dbconnwidget.connect_button.isEnabled()
    assert dbconnwidget.close_button.isEnabled()
    assert dbconnwidget.cancel_button.isEnabled()
    assert dbconnwidget.update_button.isEnabled()

    assert dbconnwidget.connect_button.isVisible()
    assert dbconnwidget.close_button.isVisible()
    assert not dbconnwidget.cancel_button.isVisible()
    assert not dbconnwidget.update_button.isVisible()


def test_dbconnwidget_connect(dbconnwidget, qtbot, mocker):
    """
    Test the database connection manager when the connection to the database
    succeed.
    """
    dbconnmanager = dbconnwidget.db_connection_manager

    def _connect_mock(*args, **kargs):
        qtbot.wait(300)
        connection = Mock()
        connection_error = None
        return connection, connection_error

    mocker.patch.object(
        DatabaseAccessorMock, '_connect', side_effect=_connect_mock)

    # Try connecting to the database.
    with qtbot.waitSignal(dbconnmanager.sig_database_connected,
                          timeout=3000):
        qtbot.mouseClick(dbconnwidget.connect_button, Qt.LeftButton)

        assert dbconnmanager.is_connecting()
        assert dbconnwidget.status_bar.status == ProcessStatusBar.IN_PROGRESS
        assert not dbconnwidget.stacked_dialogs.isEnabled()
        assert not dbconnwidget.dbtype_combobox.isEnabled()
        assert not dbconnwidget.connect_button.isEnabled()
        assert not dbconnwidget.close_button.isEnabled()
        assert not dbconnwidget.cancel_button.isVisible()
        assert not dbconnwidget.update_button.isVisible()

    # Assert that a connection to the database was created sucessfully.
    assert dbconnmanager.is_connected() is True
    assert dbconnwidget.status_bar.status == ProcessStatusBar.PROCESS_SUCCEEDED
    assert not dbconnwidget.stacked_dialogs.isEnabled()
    assert not dbconnwidget.dbtype_combobox.isEnabled()
    assert dbconnwidget.connect_button.isEnabled()
    assert dbconnwidget.connect_button.text() == 'Disconnect'
    assert dbconnwidget.close_button.isEnabled()
    assert not dbconnwidget.cancel_button.isVisible()
    assert not dbconnwidget.update_button.isVisible()
    assert not dbconnwidget.isVisible()

    dbconnwidget.show()
    qtbot.waitExposed(dbconnwidget)

    # Close the database connection.
    with qtbot.waitSignal(dbconnmanager.sig_database_disconnected):
        qtbot.mouseClick(dbconnwidget.connect_button, Qt.LeftButton)
    assert dbconnmanager.is_connected() is False
    assert dbconnwidget.status_bar.status == ProcessStatusBar.HIDDEN
    assert dbconnwidget.stacked_dialogs.isEnabled()
    assert dbconnwidget.dbtype_combobox.isEnabled()
    assert dbconnwidget.connect_button.isEnabled()
    assert dbconnwidget.connect_button.text() == 'Connect'
    assert dbconnwidget.close_button.isEnabled()
    assert not dbconnwidget.cancel_button.isVisible()
    assert not dbconnwidget.update_button.isVisible()


@pytest.mark.parametrize('mode', ['return none', 'raise exception'])
def test_dbconnwidget_failed_connect(mode, dbconnwidget, qtbot, mocker):
    """
    Test the database connection manager when the connection to the database
    fails.
    """
    dbconnmanager = dbconnwidget.db_connection_manager

    def _connect_mock(*args, **kargs):
        if mode == 'return none':
            connection = None
            connection_error = None
        elif mode == 'raise exception':
            connection = None
            connection_error = OperationalError(
                Mock(), Mock(), Mock())
        return connection, connection_error

    mocker.patch.object(
        DatabaseAccessorMock, '_connect', side_effect=_connect_mock)

    # Try connecting to the database.
    with qtbot.waitSignal(dbconnmanager.sig_database_connected):
        qtbot.mouseClick(dbconnwidget.connect_button, Qt.LeftButton)

    # Assert that the connection to the database failed.
    assert dbconnmanager.is_connected() is False
    assert dbconnwidget.status_bar.status == ProcessStatusBar.PROCESS_FAILED
    assert dbconnwidget.stacked_dialogs.isEnabled()
    assert dbconnwidget.dbtype_combobox.isEnabled()
    assert dbconnwidget.connect_button.isEnabled()
    assert dbconnwidget.close_button.isEnabled()
    assert dbconnwidget.isVisible()


def test_dbconnwidget_need_update(dbconnwidget, qtbot, mocker):
    """
    Test the database connection manager when the connection to the database
    fails because the database schema is outdated.
    """
    dbconnmanager = dbconnwidget.db_connection_manager

    # Try connecting to an outdated database.
    mocker.patch.object(
        DatabaseAccessorMock, '_connect',
        return_value=(None, DatabaseVersionError(cur_version=2, req_version=3))
        )

    with qtbot.waitSignal(dbconnmanager.sig_database_connected):
        qtbot.mouseClick(dbconnwidget.connect_button, Qt.LeftButton)

    # Assert that the connection to the database failed and is showing an
    # option to update the database.
    assert dbconnmanager.is_connected() is False
    assert dbconnwidget.status_bar.status == ProcessStatusBar.NEED_UPDATE

    assert not dbconnwidget.stacked_dialogs.isEnabled()
    assert not dbconnwidget.dbtype_combobox.isEnabled()

    assert not dbconnwidget.connect_button.isVisible()
    assert not dbconnwidget.close_button.isVisible()
    assert dbconnwidget.cancel_button.isVisible()
    assert dbconnwidget.update_button.isVisible()
    assert dbconnwidget.isVisible()

    # Update the database unsuccessfully.
    def _update_mock(*args, **kargs):
        from_version = 2
        to_version = 3
        error = DatabaseUpdateError(
            from_version,
            to_version,
            ValueError('Mocked update database error.'))
        return from_version, to_version, error

    mocker.patch.object(
        DatabaseAccessorMock, 'update_database',
        side_effect=_update_mock
        )

    with qtbot.waitSignal(dbconnmanager.sig_database_updated):
        qtbot.mouseClick(dbconnwidget.update_button, Qt.LeftButton)

    assert dbconnmanager.is_connected() is False
    assert dbconnwidget.status_bar.status == ProcessStatusBar.PROCESS_FAILED
    assert dbconnwidget.stacked_dialogs.isEnabled()
    assert dbconnwidget.dbtype_combobox.isEnabled()
    assert dbconnwidget.connect_button.isEnabled()
    assert dbconnwidget.close_button.isEnabled()
    assert dbconnwidget.isVisible()

    # Try to connect again.
    with qtbot.waitSignal(dbconnmanager.sig_database_connected):
        qtbot.mouseClick(dbconnwidget.connect_button, Qt.LeftButton)

    # Assert that the connection to the database failed again and is
    # showing again an option to update the database.
    assert dbconnmanager.is_connected() is False
    assert dbconnwidget.status_bar.status == ProcessStatusBar.NEED_UPDATE

    assert not dbconnwidget.stacked_dialogs.isEnabled()
    assert not dbconnwidget.dbtype_combobox.isEnabled()

    assert not dbconnwidget.connect_button.isVisible()
    assert not dbconnwidget.close_button.isVisible()
    assert dbconnwidget.cancel_button.isVisible()
    assert dbconnwidget.update_button.isVisible()
    assert dbconnwidget.isVisible()

    # Update the database successfully.
    def _update_mock(*args, **kargs):
        qtbot.wait(300)
        from_version = 2
        to_version = 3
        error = None
        return from_version, to_version, error

    mocker.patch.object(
        DatabaseAccessorMock, 'update_database',
        side_effect=_update_mock
        )

    with qtbot.waitSignal(dbconnmanager.sig_database_updated):
        qtbot.mouseClick(dbconnwidget.update_button, Qt.LeftButton)

        assert dbconnmanager.is_updating()
        assert dbconnwidget.status_bar.status == ProcessStatusBar.IN_PROGRESS
        assert not dbconnwidget.stacked_dialogs.isEnabled()
        assert not dbconnwidget.dbtype_combobox.isEnabled()
        assert dbconnwidget.cancel_button.isVisible()
        assert dbconnwidget.update_button.isVisible()
        assert not dbconnwidget.cancel_button.isEnabled()
        assert not dbconnwidget.update_button.isEnabled()
        assert not dbconnwidget.connect_button.isVisible()
        assert not dbconnwidget.close_button.isVisible()

    # Assert that the database was updated sucessfully.
    assert dbconnmanager.is_updating() is False
    assert dbconnwidget.status_bar.status == ProcessStatusBar.PROCESS_SUCCEEDED
    assert dbconnwidget.stacked_dialogs.isEnabled()
    assert dbconnwidget.dbtype_combobox.isEnabled()
    assert dbconnwidget.connect_button.isEnabled()
    assert dbconnwidget.close_button.isEnabled()
    assert dbconnwidget.connect_button.isVisible()
    assert dbconnwidget.close_button.isVisible()
    assert not dbconnwidget.cancel_button.isVisible()
    assert not dbconnwidget.update_button.isVisible()


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
