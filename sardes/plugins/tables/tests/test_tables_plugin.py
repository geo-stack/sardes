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
import pytest
from qtpy.QtWidgets import QMainWindow

# ---- Local imports
from sardes.database.database_manager import DatabaseConnectionManager
from sardes.database.accessor_demo import (
    DatabaseAccessorDemo, OBS_WELLS_DF, SONDE_MODELS_LIB, SONDES_DATA)
from sardes.plugins.tables import SARDES_PLUGIN_CLASS
from sardes.plugins.tables.tables.sondes_inventory import (
    SondesInventoryTableModel)
from sardes.plugins.tables.tables.observation_wells import (
    ObsWellsTableModel)


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dbconnmanager(qtbot):
    dbconnmanager = DatabaseConnectionManager()
    return dbconnmanager


@pytest.fixture
def mainwindow(qtbot, mocker, dbconnmanager):
    class MainWindowMock(QMainWindow):
        def __init__(self):
            super().__init__()
            self.panes_menu = Mock()
            self.db_connection_manager = dbconnmanager

            self.plugin = SARDES_PLUGIN_CLASS(self)
            self.plugin.register_plugin()

    mainwindow = MainWindowMock()
    mainwindow.show()
    qtbot.waitForWindowShown(mainwindow)
    qtbot.addWidget(mainwindow)

    with qtbot.waitSignal(dbconnmanager.sig_database_connected, timeout=3000):
        dbconnmanager.connect_to_db(DatabaseAccessorDemo())
    assert dbconnmanager.is_connected()
    qtbot.wait(1000)

    return mainwindow


# =============================================================================
# ---- Tests
# =============================================================================
def test_tables_plugin_init(mainwindow):
    """Test that the databse connection manager is initialized correctly."""
    assert mainwindow.plugin
    assert len(mainwindow.plugin._tables) == 2

    # Table Observation Wells.
    tablewidget = mainwindow.plugin._tables[ObsWellsTableModel.TABLE_ID]
    assert tablewidget.tableview.row_count() == len(OBS_WELLS_DF)

    # Table Sondes Inventory.
    tablewidget = mainwindow.plugin._tables[SondesInventoryTableModel.TABLE_ID]
    assert tablewidget.tableview.row_count() == len(SONDES_DATA)

# =============================================================================
# ---- Tests Table Sondes Inventory
# =============================================================================



if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
