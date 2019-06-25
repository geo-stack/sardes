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

# ---- Third party imports
from sqlalchemy.exc import OperationalError
import pytest
from qtpy.QtCore import Qt

# ---- Local imports
from sardes.widgets.databaseconnector import DatabaseConnectionWidget
from sardes.widgets.statusbar import ProcessStatusBar


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dbconnmanager(qtbot, mocker):
    dbconnmanager = DatabaseConnectionWidget()
    qtbot.addWidget(dbconnmanager)
    dbconnmanager.show()
    return dbconnmanager


# =============================================================================
# ---- Tests for DatabaseConnectionWidget
# =============================================================================
def test_dbconnmanager_init(dbconnmanager):
    """Test that the databse connection manager is initialized correctly."""
    assert dbconnmanager
    assert dbconnmanager.status_bar.status == ProcessStatusBar.HIDDEN


def test_dbconnmanager_connect(dbconnmanager, qtbot, mocker):
    """
    Test the database connection manager when the connection to the database
    succeed.
    """
    def sqlalchemy_connect_mock(*args, **kargs):
        qtbot.wait(300)
        return Mock()
    mocker.patch('sqlalchemy.engine.Engine.connect',
                 side_effect=sqlalchemy_connect_mock)

    # Try connecting to the database.
    with qtbot.waitSignal(dbconnmanager.db_conn_worker.sig_conn_finished):
        qtbot.mouseClick(dbconnmanager.connect_button, Qt.LeftButton)

        assert dbconnmanager.status_bar.status == ProcessStatusBar.IN_PROGRESS
        assert not dbconnmanager.form_groupbox.isEnabled()
        assert not dbconnmanager.connect_button.isEnabled()
        assert not dbconnmanager.reset_button.isEnabled()
        assert not dbconnmanager.ok_button.isEnabled()

    # Assert that a connection to the database was created sucessfully.
    assert dbconnmanager.conn is not None
    assert (dbconnmanager.status_bar.status ==
            ProcessStatusBar.PROCESS_SUCCEEDED)
    assert not dbconnmanager.form_groupbox.isEnabled()
    assert dbconnmanager.connect_button.isEnabled()
    assert dbconnmanager.connect_button.text() == 'Disconnect'
    assert not dbconnmanager.reset_button.isEnabled()
    assert dbconnmanager.ok_button.isEnabled()

    # Close the database connection.
    qtbot.mouseClick(dbconnmanager.connect_button, Qt.LeftButton)
    assert dbconnmanager.conn is None
    assert dbconnmanager.status_bar.status == ProcessStatusBar.HIDDEN
    assert dbconnmanager.form_groupbox.isEnabled()
    assert dbconnmanager.connect_button.isEnabled()
    assert dbconnmanager.connect_button.text() == 'Connect'
    assert dbconnmanager.reset_button.isEnabled()
    assert dbconnmanager.ok_button.isEnabled()


@pytest.mark.parametrize('mode', ['return none', 'raise exception'])
def test_dbconnmanager_failed_connect(mode, dbconnmanager, qtbot, mocker):
    """
    Test the database connection manager when the connection to the database
    fails.
    """
    def sqlalchemy_connect_mock(*args, **kargs):
        qtbot.wait(300)
        if mode == 'return none':
            return None
        elif mode == 'raise exception':
            raise OperationalError(Mock(), Mock(), Mock())
    mocker.patch('sqlalchemy.engine.Engine.connect',
                 side_effect=sqlalchemy_connect_mock)

    # Try connecting to the database.
    with qtbot.waitSignal(dbconnmanager.db_conn_worker.sig_conn_finished):
        qtbot.mouseClick(dbconnmanager.connect_button, Qt.LeftButton)

        assert dbconnmanager.status_bar.status == ProcessStatusBar.IN_PROGRESS
        assert not dbconnmanager.form_groupbox.isEnabled()
        assert not dbconnmanager.connect_button.isEnabled()
        assert not dbconnmanager.reset_button.isEnabled()
        assert not dbconnmanager.ok_button.isEnabled()

    # Assert that the connection to the database failed.
    assert dbconnmanager.conn is None
    assert dbconnmanager.status_bar.status == ProcessStatusBar.PROCESS_FAILED
    assert dbconnmanager.form_groupbox.isEnabled()
    assert dbconnmanager.connect_button.isEnabled()
    assert dbconnmanager.reset_button.isEnabled()
    assert dbconnmanager.ok_button.isEnabled()


if __name__ == "__main__":
    pytest.main(['-x', os.path.basename(__file__), '-v', '-rw'])
