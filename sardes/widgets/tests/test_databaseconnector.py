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
import os.path as osp
from unittest.mock import Mock

# ---- Third party imports
from sqlalchemy.exc import OperationalError
import pytest
from qtpy.QtCore import Qt

# ---- Local imports
from sardes.database.manager import DatabaseConnectionManager
from sardes.widgets.databaseconnector import DatabaseConnectionWidget
from sardes.widgets.statusbar import ProcessStatusBar


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
    with qtbot.waitSignal(dbconnmanager.sig_database_connected):
        qtbot.mouseClick(dbconnwidget.connect_button, Qt.LeftButton)

        assert dbconnmanager.is_connecting()
        assert dbconnwidget.status_bar.status == ProcessStatusBar.IN_PROGRESS
        assert not dbconnwidget.form_groupbox.isEnabled()
        assert not dbconnwidget.connect_button.isEnabled()
        assert not dbconnwidget.reset_button.isEnabled()
        assert not dbconnwidget.ok_button.isEnabled()

    # Assert that a connection to the database was created sucessfully.
    assert dbconnmanager.is_connected() is True
    assert (dbconnwidget.status_bar.status ==
            ProcessStatusBar.PROCESS_SUCCEEDED)
    assert not dbconnwidget.form_groupbox.isEnabled()
    assert dbconnwidget.connect_button.isEnabled()
    assert dbconnwidget.connect_button.text() == 'Disconnect'
    assert not dbconnwidget.reset_button.isEnabled()
    assert dbconnwidget.ok_button.isEnabled()

    # Close the database connection.
    with qtbot.waitSignal(dbconnmanager.sig_database_disconnected):
        qtbot.mouseClick(dbconnwidget.connect_button, Qt.LeftButton)
    assert dbconnmanager.is_connected() is False
    assert dbconnwidget.status_bar.status == ProcessStatusBar.HIDDEN
    assert dbconnwidget.form_groupbox.isEnabled()
    assert dbconnwidget.connect_button.isEnabled()
    assert dbconnwidget.connect_button.text() == 'Connect'
    assert dbconnwidget.reset_button.isEnabled()
    assert dbconnwidget.ok_button.isEnabled()


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
    with qtbot.waitSignal(dbconnmanager.sig_database_connected):
        qtbot.mouseClick(dbconnwidget.connect_button, Qt.LeftButton)

        assert dbconnmanager.is_connecting()
        assert dbconnwidget.status_bar.status == ProcessStatusBar.IN_PROGRESS
        assert not dbconnwidget.form_groupbox.isEnabled()
        assert not dbconnwidget.connect_button.isEnabled()
        assert not dbconnwidget.reset_button.isEnabled()
        assert not dbconnwidget.ok_button.isEnabled()

    # Assert that the connection to the database failed.
    assert dbconnmanager.is_connected() is False
    assert dbconnwidget.status_bar.status == ProcessStatusBar.PROCESS_FAILED
    assert dbconnwidget.form_groupbox.isEnabled()
    assert dbconnwidget.connect_button.isEnabled()
    assert dbconnwidget.reset_button.isEnabled()
    assert dbconnwidget.ok_button.isEnabled()


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
