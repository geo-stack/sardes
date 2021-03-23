# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the Tables plugin.
"""

# ---- Standard imports
import datetime
import os
import os.path as osp
from unittest.mock import Mock
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pytest
from qtpy.QtCore import Qt, QUrl
from qtpy.QtGui import QDesktopServices

# ---- Local imports
from sardes.plugins.tables import SARDES_PLUGIN_CLASS
from sardes.widgets.tableviews import MSEC_MIN_PROGRESS_DISPLAY
from sardes.database.accessors import DatabaseAccessorSardesLite
from sardes.app.mainwindow import MainWindowBase


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dbaccessor(tmp_path, database_filler):
    dbaccessor = DatabaseAccessorSardesLite(
        osp.join(tmp_path, 'sqlite_database_test.db'))
    dbaccessor.init_database()
    database_filler(dbaccessor)

    return dbaccessor


@pytest.fixture
def mainwindow(qtbot, mocker, dbaccessor):
    class MainWindowMock(MainWindowBase):
        def __init__(self):
            self.view_timeseries_data = Mock()
            super().__init__()

        def setup_internal_plugins(self):
            self.plugin = SARDES_PLUGIN_CLASS(self)
            self.plugin.register_plugin()
            self.internal_plugins.append(self.plugin)

    mainwindow = MainWindowMock()
    mainwindow.show()
    qtbot.waitForWindowShown(mainwindow)

    dbconnmanager = mainwindow.db_connection_manager
    with qtbot.waitSignal(dbconnmanager.sig_database_connected, timeout=3000):
        dbconnmanager.connect_to_db(dbaccessor)
    assert dbconnmanager.is_connected()
    qtbot.wait(1000)

    yield mainwindow

    # We need to wait for the mainwindow to close properly to avoid
    # runtime errors on the c++ side.
    with qtbot.waitSignal(mainwindow.sig_about_to_close):
        mainwindow.close()


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
# ---- Tests Table Observation Wells
# =============================================================================
def test_show_in_google_maps(mainwindow, qtbot, mocker):
    """
    Test that the tool to show the currently selected well in Google maps is
    working as expected.
    """
    tablewidget = mainwindow.plugin._tables['table_observation_wells']
    tableview = tablewidget.tableview
    tablemodel = tablewidget.model()

    # Select the tab corresponding to the manual measurements.
    mainwindow.plugin.tabwidget.setCurrentWidget(tablewidget)
    qtbot.wait(300)

    # We are selecting the first well in the table.
    selection_model = tableview.selectionModel()
    selection_model.setCurrentIndex(
        tablemodel.index(0, 0), selection_model.SelectCurrent)

    # We are patching QDesktopServices.openUrl because we don't want to
    # slow down tests by opening web pages on an external browser.
    patcher_qdesktopservices = mocker.patch.object(
        QDesktopServices, 'openUrl', return_value=True)
    tablewidget.show_in_google_maps()
    patcher_qdesktopservices.assert_called_once_with(QUrl(
        'https://www.google.com/maps/search/?api=1&query=45.445178,-72.828773'
        ))


# =============================================================================
# ---- Tests Table Manual Measurements
# =============================================================================
def test_table_manual_measurements(mainwindow, qtbot, dbaccessor,
                                   manual_measurements, obswells_data):
    tablewidget = mainwindow.plugin._tables['table_manual_measurements']
    tableview = tablewidget.tableview
    tablemodel = tablewidget.model()

    # Select the tab corresponding to the manual measurements.
    mainwindow.plugin.tabwidget.setCurrentWidget(tablewidget)
    qtbot.wait(300)

    assert mainwindow.plugin.current_table() == tablewidget
    assert tableview.row_count() == len(manual_measurements)
    assert tableview.column_count() == len(manual_measurements.columns)

    # Add a new manual measurement.
    new_row = len(manual_measurements)
    tableview.new_row_action.trigger()
    assert tablemodel.data_edit_count() == 1
    assert tableview.row_count() == len(manual_measurements) + 1
    assert (tableview.get_data_for_row(new_row) == ['', '', '', ''])

    # Save the edits.
    with qtbot.waitSignal(tablemodel.sig_data_updated):
        tablemodel.save_data_edits()
    assert tablemodel.data_edit_count() == 0
    assert (tableview.get_data_for_row(new_row) == ['', '', '', ''])

    # Edit the data of the newly added row.
    edited_data = [obswells_data.index[1],
                   datetime.datetime(2001, 8, 2, 12, 34, 20),
                   1.2345,
                   'test_edit_newrow']
    for i, value in enumerate(edited_data):
        model_index = tablemodel.index(new_row, i)
        assert tableview.is_data_editable_at(model_index)
        tablemodel.set_data_edit_at(model_index, value)

    assert tablemodel.data_edit_count() == i + 1
    assert (tableview.get_data_for_row(new_row) ==
            ['02200001', '2001-08-02 12:34', '1.2345', 'test_edit_newrow'])

    # Save the edits.
    with qtbot.waitSignal(tablemodel.sig_data_updated):
        tablemodel.save_data_edits()
    assert tablemodel.data_edit_count() == 0
    assert (tableview.get_data_for_row(new_row) ==
            ['02200001', '2001-08-02 12:34', '1.2345', 'test_edit_newrow'])

    # Delete the last two rows of the table.
    selection_model = tableview.selectionModel()
    selection_model.setCurrentIndex(
        tablemodel.index(new_row, 0), selection_model.SelectCurrent)
    selection_model.select(
        tablemodel.index(new_row - 1, 0), selection_model.Select)
    assert (tableview.get_rows_intersecting_selection() ==
            [new_row - 1, new_row])

    tableview.delete_row_action.trigger()
    assert tablemodel.data_edit_count() == 1

    # Save the edits.
    with qtbot.waitSignal(tablemodel.sig_data_updated):
        tablemodel.save_data_edits()
    assert tablemodel.data_edit_count() == 0
    assert tableview.row_count() == len(manual_measurements) - 1


# =============================================================================
# ---- Tests Table Sondes Inventory
# =============================================================================
def test_edit_sonde_model(mainwindow, qtbot, dbaccessor):
    """
    Test editing sonde brand in the sondes inventory table.
    """
    sonde_models_lib = dbaccessor.get_sonde_models_lib()
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
    assert model.get_value_at(model_index) == 5

    qtbot.mouseClick(
        tableview.viewport(),
        Qt.LeftButton,
        pos=tableview.visualRect(model_index).center())

    # Enable editing mode on the selected cell.
    qtbot.keyPress(tableview, Qt.Key_Enter)
    assert tableview.state() == tableview.EditingState

    # Assert the editor of the item delegate is showing the right data.
    editor = tableview.itemDelegate(model_index).editor
    assert editor.currentData() == 5
    assert editor.currentText() == 'Solinst Barologger M1.5'
    assert editor.count() == len(sonde_models_lib)

    # Select a new value and accept the edit.
    editor.setCurrentIndex(editor.findData(8))
    qtbot.keyPress(editor, Qt.Key_Enter)
    assert tableview.state() != tableview.EditingState
    assert model_index.data() == 'Solinst LTC F30/M10'
    assert model.get_value_at(model_index) == 8
    assert tabwidget.tabText(1) == tablewidget.get_table_title() + '*'

    # Undo the last edit.
    tableview._undo_last_data_edit()
    assert model_index.data() == 'Solinst Barologger M1.5'
    assert model.get_value_at(model_index) == 5
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


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
