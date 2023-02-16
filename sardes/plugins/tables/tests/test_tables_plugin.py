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
from qtpy.QtCore import Qt

# ---- Local imports
from sardes.config.main import CONF
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

    CONF.reset_to_defaults()

    mainwindow = MainWindowMock()
    mainwindow.show()
    qtbot.waitExposed(mainwindow)

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
    models_manager = mainwindow.table_models_manager

    assert mainwindow.plugin
    assert mainwindow.plugin.table_count() == 6
    assert len(models_manager._table_models) == 6
    assert tabwidget.currentIndex() == 0

    # Table Observation Wells.
    for current_index in range(mainwindow.plugin.table_count()):
        tabwidget.setCurrentIndex(current_index)
        qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)
        assert tabwidget.currentWidget() == plugin.current_table()
        for index in range(mainwindow.plugin.table_count()):
            table = tabwidget.widget(index)
            table_id = table.table_name()
            if index <= current_index:
                assert table.tableview.row_count() > 0
                assert len(models_manager._queued_model_updates[table_id]) == 0
            else:
                assert table.tableview.row_count() == 0
                assert (len(models_manager._queued_model_updates[table_id]) ==
                        len(table.model().__libnames__) + 1)
            assert tabwidget.tabText(index) == table.table_title()


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
def test_edit_sonde_model(mainwindow, qtbot, dbaccessor):
    """
    Test editing sonde brand in the sondes inventory table.
    """
    sonde_models_lib = dbaccessor.get('sonde_models_lib')
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
    assert tabwidget.tabText(1) == tablewidget.table_title() + '*'

    # Undo the last edit.
    tableview._undo_edit()
    assert model_index.data() == 'Solinst Barologger M1.5'
    assert model.get_value_at(model_index) == 5
    assert tabwidget.tabText(1) == tablewidget.table_title()


def test_save_data_edits(mainwindow, qtbot):
    """
    Assert that tables data is updated correctly after edits are saved.
    """
    table_obs_well = mainwindow.plugin._tables['table_observation_wells']
    table_man_meas = mainwindow.plugin._tables['table_manual_measurements']

    # We need first to select the tab corresponding to the table manual
    # measurements and assert the value displayed in cell at index (1, 1).
    mainwindow.plugin.tabwidget.setCurrentWidget(table_man_meas)
    qtbot.waitUntil(
        lambda: table_man_meas.model().index(0, 0).data() == '03037041',
        timeout=3000)

    # We now switch to table observation wells and do an edit to the table's
    # data programmatically.
    mainwindow.plugin.tabwidget.setCurrentWidget(table_obs_well)
    qtbot.waitUntil(
        lambda: table_obs_well.model().index(0, 0).data() == '03037041',
        timeout=3000)

    table_obs_well.tableview.model().set_data_edit_at(
        table_obs_well.model().index(0, 0), '03037041_modif')
    assert table_obs_well.model().index(0, 0).data() == '03037041_modif'

    # We now save the edits.
    table_obs_well.model().save_data_edits()

    # We switch back to table manual measurements and assert that the changes
    # made in table observation wells are reflected here as expected.
    mainwindow.plugin.tabwidget.setCurrentWidget(table_man_meas)
    qtbot.waitUntil(
        lambda: table_man_meas.model().index(0, 0).data() == '03037041_modif',
        timeout=3000)


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
