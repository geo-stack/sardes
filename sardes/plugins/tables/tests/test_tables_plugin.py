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
# ---- Standard imports
import os
import os.path as osp
from unittest.mock import Mock
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pytest
from qtpy.QtCore import Qt
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
    qtbot.wait(1500)

    return mainwindow


# =============================================================================
# ---- Tests
# =============================================================================
def test_tables_plugin_init(mainwindow):
    """Test that the databse connection manager is initialized correctly."""
    assert mainwindow.plugin
    assert len(mainwindow.plugin._tables) == 3

    # Table Observation Wells.
    tablewidget = mainwindow.plugin._tables[ObsWellsTableModel.TABLE_ID]
    assert tablewidget.tableview.row_count() == len(OBS_WELLS_DF)

    # Table Sondes Inventory.
    tablewidget = mainwindow.plugin._tables[SondesInventoryTableModel.TABLE_ID]
    assert tablewidget.tableview.row_count() == len(SONDES_DATA)


# =============================================================================
# ---- Tests Table Sondes Inventory
# =============================================================================
def test_edit_sonde_model(mainwindow, qtbot):
    """
    Test editing sonde brand in the sondes inventory table.
    """
    tablewidget = mainwindow.plugin._tables[SondesInventoryTableModel.TABLE_ID]
    tableview = tablewidget.tableview
    model = tablewidget.tableview.model()

    # We need to select the tab corresponding to the table sondes inventory.
    mainwindow.plugin.tabwidget.setCurrentWidget(tablewidget)

    # Select the first cell of the table.
    model_index = tableview.model().index(0, 0)
    assert model_index.data() == 'Solinst Barologger M1.5 Gold'
    assert model.get_value_at(model_index) == 0

    qtbot.mouseClick(
        tableview.viewport(),
        Qt.LeftButton,
        pos=tableview.visualRect(model_index).center())

    # Enable editing mode on the selected cell.
    qtbot.keyPress(tableview, Qt.Key_Enter)
    assert tableview.state() == tableview.EditingState

    # Assert the editor of the item delegate is showing the right data.
    editor = tableview.itemDelegate(model_index).editor
    assert editor.currentData() == 0
    assert editor.currentText() == 'Solinst Barologger M1.5 Gold'
    assert editor.count() == len(SONDE_MODELS_LIB)

    # Select a new value and accept the edit.
    editor.setCurrentIndex(editor.findData(7))
    qtbot.keyPress(editor, Qt.Key_Enter)
    assert tableview.state() != tableview.EditingState
    assert model_index.data() == 'Telog 2 Druck'
    assert model.get_value_at(model_index) == 7

    # Undo the last edit.
    tableview._undo_last_data_edit()
    assert model_index.data() == 'Solinst Barologger M1.5 Gold'
    assert model.get_value_at(model_index) == 0


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
