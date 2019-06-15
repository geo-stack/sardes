# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for database/connection.py.
"""

# ---- Standard imports
import os
from unittest.mock import Mock

# ---- Third party imports
import psycopg2
import pytest
from qtpy.QtCore import Qt

# ---- Local imports
from sardes.database.connection import BDConnManager
from sardes.widgets.statusbar import ProcessStatusBar


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dbconnmanager(qtbot, mocker):
    dbconnmanager = BDConnManager()
    qtbot.addWidget(dbconnmanager)
    dbconnmanager.show()
    return dbconnmanager


# =============================================================================
# ---- Tests for BDConnManager
# =============================================================================
def test_dbconnmanager_init(dbconnmanager):
    """Test that the BDConnManager is initialized correctly."""
    assert dbconnmanager
    assert dbconnmanager.status_bar.status == ProcessStatusBar.HIDDEN


def test_dbconnmanager_connect(dbconnmanager, qtbot, mocker):
    """
    Test the database connection manager when the connection to the database
    succeed.
    """
    def psycopg2_connect_mock(*args, **kargs):
        qtbot.wait(300)
        return Mock()
    mocker.patch('psycopg2.connect', side_effect=psycopg2_connect_mock)

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
    def psycopg2_connect_mock(*args, **kargs):
        qtbot.wait(300)
        if mode == 'return none':
            return None
        elif mode == 'raise exception':
            raise psycopg2.OperationalError
    mocker.patch('psycopg2.connect', side_effect=psycopg2_connect_mock)

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
