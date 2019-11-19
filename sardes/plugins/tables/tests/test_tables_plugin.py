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
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMainWindow

# ---- Local imports
from sardes.database.database_manager import DatabaseConnectionManager
from sardes.database.accessor_demo import DatabaseAccessorDemo
from sardes.plugins.tables import SARDES_PLUGIN_CLASS
from sardes.database.accessor_demo import SONDE_MODELS_LIB


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
def test_tables_plugin_init(mainwindow, qtbot):
    """Test that the databse connection manager is initialized correctly."""
    tabwidget = mainwindow.plugin.tabwidget
    plugin = mainwindow.plugin

    assert mainwindow.plugin
    assert mainwindow.plugin.table_count() == 3

    # Table Observation Wells.
    for current_index in range(mainwindow.plugin.table_count()):
        tabwidget.setCurrentIndex(current_index)
        qtbot.wait(1000)
        assert tabwidget.currentWidget() == plugin.current_table()
        for index in range(mainwindow.plugin.table_count()):
            table = tabwidget.widget(index)
            table_id = table.get_table_id()
            if index <= current_index:
                assert table.tableview.row_count() > 0
                assert len(plugin._table_updates[table_id]) == 0
            else:
                assert table.tableview.row_count() == 0
                assert (len(plugin._table_updates[table_id]) ==
                        len(table.model().req_data_names()))
            assert tabwidget.tabText(index) == table.get_table_title()


# =============================================================================
# ---- Tests Table Sondes Inventory
# =============================================================================
def test_edit_sonde_model(mainwindow, qtbot):
    """
    Test editing sonde brand in the sondes inventory table.
    """
    tabwidget = mainwindow.plugin.tabwidget
    tablewidget = mainwindow.plugin._tables['table_sondes_inventory']
    tableview = tablewidget.tableview
    model = tablewidget.tableview.model()

    # We need to select the tab corresponding to the table sondes inventory.
    mainwindow.plugin.tabwidget.setCurrentWidget(tablewidget)
    qtbot.wait(1000)

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
    assert tabwidget.tabText(1) == tablewidget.get_table_title() + '*'

    # Undo the last edit.
    tableview._undo_last_data_edit()
    assert model_index.data() == 'Solinst Barologger M1.5 Gold'
    assert model.get_value_at(model_index) == 0
    assert tabwidget.tabText(1) == tablewidget.get_table_title()


def test_save_data_edits(mainwindow, qtbot):
    """
    Assert that tables data is updated correctly after edits are saved.
    """
    table_obs_well = mainwindow.plugin._tables['table_observation_wells']
    table_man_meas = mainwindow.plugin._tables['table_manual_measurements']

    # We need first to select the tab corresponding to the table manual
    # measurements and assert the value displayed in cell at index (1, 1).
    mainwindow.plugin.tabwidget.setCurrentWidget(table_man_meas)
    qtbot.wait(1000)
    model_index = table_man_meas.tableview.model().index(0, 0)
    assert model_index.data() == '0343128'

    # We now switch to table observation wells and do an edit to the table's
    # data programmatically.
    mainwindow.plugin.tabwidget.setCurrentWidget(table_obs_well)
    qtbot.wait(1000)
    model_index = table_obs_well.tableview.model().index(0, 0)
    assert model_index.data() == '0343128'
    table_obs_well.tableview.model().set_data_edits_at(
        model_index, '0343128_modif')
    assert model_index.data() == '0343128_modif'

    # We now save the edits.
    table_obs_well.tableview.model().save_data_edits()
    qtbot.wait(100)

    # We switch back to table manual measurements and assert that the changes
    # made in table observation wells were reflected here as expected.
    mainwindow.plugin.tabwidget.setCurrentWidget(table_man_meas)
    qtbot.wait(1000)
    model_index = table_man_meas.tableview.model().index(0, 0)
    assert model_index.data() == '0343128_modif'


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
