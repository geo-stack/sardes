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
from sardes.widgets.tableviews import (MSEC_MIN_PROGRESS_DISPLAY, QMessageBox)


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
    models_manager = mainwindow.db_connection_manager.models_manager

    assert mainwindow.plugin
    assert mainwindow.plugin.table_count() == 5
    assert len(models_manager._table_models) == 5

    # Table Observation Wells.
    for current_index in range(mainwindow.plugin.table_count()):
        tabwidget.setCurrentIndex(current_index)
        qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)
        assert tabwidget.currentWidget() == plugin.current_table()
        for index in range(mainwindow.plugin.table_count()):
            table = tabwidget.widget(index)
            table_id = table.get_table_id()
            if index <= current_index:
                assert table.tableview.row_count() > 0
                assert len(models_manager._queued_model_updates[table_id]) == 0
            else:
                assert table.tableview.row_count() == 0
                assert (len(models_manager._queued_model_updates[table_id]) ==
                        len(models_manager._models_req_data[table_id]))
            assert tabwidget.tabText(index) == table.get_table_title()


def test_disconnect_from_database(mainwindow, qtbot):
    """
    Test that the data are cleared as expected when disconnecting from the
    database.
    """
    # Circle through all tables so that their data are fetched from the
    # database.
    tabwidget = mainwindow.plugin.tabwidget
    for index in range(mainwindow.plugin.table_count()):
        tabwidget.setCurrentIndex(index)
        qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)
        table = tabwidget.widget(index)
        assert table.tableview.row_count() > 0

    # Disconnect from the database.
    mainwindow.db_connection_manager.disconnect_from_db()
    qtbot.wait(300)
    for index in range(mainwindow.plugin.table_count()):
        table = tabwidget.widget(index)
        assert table.tableview.row_count() == 0


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
    assert model_index.data() == 'Solinst Barologger M1.5'
    assert model.get_value_at(model_index) == 3

    qtbot.mouseClick(
        tableview.viewport(),
        Qt.LeftButton,
        pos=tableview.visualRect(model_index).center())

    # Enable editing mode on the selected cell.
    qtbot.keyPress(tableview, Qt.Key_Enter)
    assert tableview.state() == tableview.EditingState

    # Assert the editor of the item delegate is showing the right data.
    editor = tableview.itemDelegate(model_index).editor
    assert editor.currentData() == 3
    assert editor.currentText() == 'Solinst Barologger M1.5'
    assert editor.count() == len(SONDE_MODELS_LIB)

    # Select a new value and accept the edit.
    editor.setCurrentIndex(editor.findData(8))
    qtbot.keyPress(editor, Qt.Key_Enter)
    assert tableview.state() != tableview.EditingState
    assert model_index.data() == 'Telog 2 Druck'
    assert model.get_value_at(model_index) == 8
    assert tabwidget.tabText(1) == tablewidget.get_table_title() + '*'

    # Undo the last edit.
    tableview._undo_last_data_edit()
    assert model_index.data() == 'Solinst Barologger M1.5'
    assert model.get_value_at(model_index) == 3
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
    assert model_index.data() == '03037041'

    # We now switch to table observation wells and do an edit to the table's
    # data programmatically.
    mainwindow.plugin.tabwidget.setCurrentWidget(table_obs_well)
    qtbot.wait(1000)
    model_index = table_obs_well.tableview.model().index(0, 0)
    assert model_index.data() == '03037041'
    table_obs_well.tableview.model().set_data_edit_at(
        model_index, '03037041_modif')
    assert model_index.data() == '03037041_modif'

    # We now save the edits.
    table_obs_well.tableview.model().save_data_edits()
    qtbot.wait(100)

    # We switch back to table manual measurements and assert that the changes
    # made in table observation wells were reflected here as expected.
    mainwindow.plugin.tabwidget.setCurrentWidget(table_man_meas)
    qtbot.wait(1000)
    model_index = table_man_meas.tableview.model().index(0, 0)
    assert model_index.data() == '03037041_modif'


# =============================================================================
# ---- Tests Time Series Table
# =============================================================================
def test_view_timeseries_data(mainwindow, qtbot):
    """
    Assert that timeseries data tables are created and shown as expected.
    """
    tables_plugin = mainwindow.plugin
    table_obs_well = mainwindow.plugin._tables['table_observation_wells']
    tables_plugin.tabwidget.setCurrentWidget(table_obs_well)
    qtbot.wait(1000)
    table_obs_well.tableview.model().index(0, 0)

    current_obs_well = table_obs_well.get_current_obs_well_data().name
    assert current_obs_well == 0

    assert len(tables_plugin._tseries_data_tables) == 0
    qtbot.mouseClick(table_obs_well.show_data_btn, Qt.LeftButton)
    qtbot.wait(1000)
    assert len(tables_plugin._tseries_data_tables) == 1
    assert tables_plugin._tseries_data_tables[current_obs_well].isVisible()

    table = tables_plugin._tseries_data_tables[0]
    assert table.tableview.row_count() == 1826


def test_delete_timeseries_data(mainwindow, qtbot, mocker):
    """
    Test that deleting data in a timeseries data table is working as
    expected.

    Regression test for cgq-qgc/sardes#210
    """
    tables_plugin = mainwindow.plugin
    table_obs_well = mainwindow.plugin._tables['table_observation_wells']
    tables_plugin.tabwidget.setCurrentWidget(table_obs_well)
    qtbot.waitUntil(lambda: table_obs_well.tableview.row_count() > 0)

    # View data table for the firs observation well.
    qtbot.mouseClick(table_obs_well.show_data_btn, Qt.LeftButton)
    qtbot.waitUntil(lambda: len(tables_plugin._tseries_data_tables) == 1)
    qtbot.waitForWindowShown(tables_plugin._tseries_data_tables[0])

    tableview = tables_plugin._tseries_data_tables[0].tableview
    selection_model = tableview.selectionModel()
    model = tableview.model()
    assert tableview.row_count() == 1826

    # Select one row in the table.
    selection_model.setCurrentIndex(
        model.index(3, 0), selection_model.SelectCurrent)
    assert tableview.get_selected_rows() == [3]
    assert tableview.delete_row_action.isEnabled()

    # Delete the selected row.
    tableview.delete_row_action.trigger()
    assert not tableview.delete_row_action.isEnabled()
    assert tableview.model().data_edit_count() == 1
    assert model.has_unsaved_data_edits() is True

    # Select more rows in the table.
    selection_model.select(model.index(1, 1), selection_model.Select)
    selection_model.select(model.index(4, 1), selection_model.Select)
    selection_model.select(model.index(5, 1), selection_model.Select)
    assert tableview.get_selected_rows() == [1, 3, 4, 5]
    assert tableview.delete_row_action.isEnabled()

    # Delete the selected rows.
    tableview.delete_row_action.trigger()
    assert not tableview.delete_row_action.isEnabled()
    assert model.data_edit_count() == 2
    assert model.has_unsaved_data_edits() is True

    # Commit the row deletions to the database.
    mocker.patch.object(QMessageBox, 'exec_', return_value=QMessageBox.Save)
    with qtbot.waitSignal(model.sig_data_updated, timeout=3000):
        tableview.save_edits_action.trigger()
    assert model.data_edit_count() == 0
    assert model.has_unsaved_data_edits() is False
    assert tableview.row_count() == 1826 - 4

    # Close the timeseries table.
    tables_plugin._tseries_data_tables[0].close()
    qtbot.waitUntil(lambda: len(tables_plugin._tseries_data_tables) == 0)
    qtbot.wait(300)


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
