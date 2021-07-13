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
import os.path as osp
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
from sardes.database.dialog_rsesq import (
    DatabaseConnectDialogRSESQ as DatabaseConnectDialog)


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dbconnmanager():
    dbconnmanager = DatabaseConnectionManager()
    return dbconnmanager


@pytest.fixture
def dbconnwidget(qtbot, mocker, dbconnmanager):
    dbconnwidget = DatabaseConnectionWidget(dbconnmanager)

    # Add a database connection dialog to the database connection widget.
    database_dialog = DatabaseConnectDialog()
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


def test_dbconnwidget_connect(dbconnwidget, qtbot, mocker):
    """
    Test the database connection manager when the connection to the database
    succeed.
    """
    dbconnmanager = dbconnwidget.db_connection_manager

    def sqlalchemy_connect_mock(*args, **kargs):
        qtbot.wait(300)
        mocked_connection = Mock()
        mocked_connection.closed = False
        return mocked_connection
    mocker.patch('sqlalchemy.engine.Engine.connect',
                 side_effect=sqlalchemy_connect_mock)

    # Try connecting to the database.
    with qtbot.waitSignal(dbconnmanager.sig_database_connected,
                          timeout=3000):
        qtbot.mouseClick(dbconnwidget.connect_button, Qt.LeftButton)

        assert dbconnmanager.is_connecting()
        assert dbconnwidget.status_bar.status == ProcessStatusBar.IN_PROGRESS
        assert not dbconnwidget.stacked_dialogs.isEnabled()
        assert not dbconnwidget.connect_button.isEnabled()
        assert not dbconnwidget.close_button.isEnabled()

    # Assert that a connection to the database was created sucessfully.
    assert dbconnmanager.is_connected() is True
    assert (dbconnwidget.status_bar.status ==
            ProcessStatusBar.PROCESS_SUCCEEDED)
    assert not dbconnwidget.stacked_dialogs.isEnabled()
    assert dbconnwidget.connect_button.isEnabled()
    assert dbconnwidget.connect_button.text() == 'Disconnect'
    assert dbconnwidget.close_button.isEnabled()
    assert not dbconnwidget.isVisible()

    dbconnwidget.show()
    qtbot.waitExposed(dbconnwidget)

    # Close the database connection.
    with qtbot.waitSignal(dbconnmanager.sig_database_disconnected):
        qtbot.mouseClick(dbconnwidget.connect_button, Qt.LeftButton)
    assert dbconnmanager.is_connected() is False
    assert dbconnwidget.status_bar.status == ProcessStatusBar.HIDDEN
    assert dbconnwidget.stacked_dialogs.isEnabled()
    assert dbconnwidget.connect_button.isEnabled()
    assert dbconnwidget.connect_button.text() == 'Connect'
    assert dbconnwidget.close_button.isEnabled()


@pytest.mark.parametrize('mode', ['return none', 'raise exception'])
def test_dbconnwidget_failed_connect(mode, dbconnwidget, qtbot, mocker):
    """
    Test the database connection manager when the connection to the database
    fails.
    """
    dbconnmanager = dbconnwidget.db_connection_manager

    def sqlalchemy_connect_mock(*args, **kargs):
        qtbot.wait(300)
        if mode == 'return none':
            return None
        elif mode == 'raise exception':
            raise OperationalError(Mock(), Mock(), Mock())
    mocker.patch('sqlalchemy.engine.Engine.connect',
                 side_effect=sqlalchemy_connect_mock)

    # Try connecting to the database.
    with qtbot.waitSignal(dbconnmanager.sig_database_connected,
                          timeout=3000):
        qtbot.mouseClick(dbconnwidget.connect_button, Qt.LeftButton)

        assert dbconnmanager.is_connecting()
        assert dbconnwidget.status_bar.status == ProcessStatusBar.IN_PROGRESS
        assert not dbconnwidget.stacked_dialogs.isEnabled()
        assert not dbconnwidget.connect_button.isEnabled()
        assert not dbconnwidget.close_button.isEnabled()

    # Assert that the connection to the database failed.
    assert dbconnmanager.is_connected() is False
    assert dbconnwidget.status_bar.status == ProcessStatusBar.PROCESS_FAILED
    assert dbconnwidget.stacked_dialogs.isEnabled()
    assert dbconnwidget.connect_button.isEnabled()
    assert dbconnwidget.close_button.isEnabled()
    assert dbconnwidget.isVisible()


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
