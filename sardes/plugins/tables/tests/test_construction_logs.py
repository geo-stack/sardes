# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the ObsWellsTableWidget construction well tool.
"""

# ---- Standard imports
import os
import os.path as osp
from unittest.mock import Mock
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pytest
from qtpy.QtCore import QPoint
from qtpy.QtWidgets import QMainWindow, QFileDialog

# ---- Local imports
from sardes.database.database_manager import DatabaseConnectionManager
from sardes.plugins.tables import SARDES_PLUGIN_CLASS
from sardes.widgets.tableviews import MSEC_MIN_PROGRESS_DISPLAY
from sardes.database.accessors.accessor_sardes_lite import (
    DatabaseAccessorSardesLite)


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dbaccessor(tmp_path, obswells_data):
    dbaccessor = DatabaseAccessorSardesLite(
        osp.join(tmp_path, 'sqlite_database_test.db'))
    dbaccessor.init_database()

    # Add observation wells to the database.
    for obs_well_uuid, obs_well_data in obswells_data.iterrows():
        dbaccessor.add_observation_wells_data(
            obs_well_uuid, attribute_values=obs_well_data.to_dict())
    return dbaccessor


@pytest.fixture
def dbconnmanager(qtbot):
    dbconnmanager = DatabaseConnectionManager()
    return dbconnmanager


@pytest.fixture
def mainwindow(qtbot, mocker, dbconnmanager, dbaccessor):
    class MainWindowMock(QMainWindow):
        def __init__(self):
            super().__init__()
            self.panes_menu = Mock()
            self.db_connection_manager = dbconnmanager

            self.view_timeseries_data = Mock()
            self.plot_timeseries_data = Mock()

            self.register_table = Mock()
            self.unregister_table = Mock()

            self.plugin = SARDES_PLUGIN_CLASS(self)
            self.plugin.register_plugin()

    mainwindow = MainWindowMock()
    mainwindow.show()
    qtbot.waitForWindowShown(mainwindow)
    qtbot.addWidget(mainwindow)

    with qtbot.waitSignal(dbconnmanager.sig_database_connected, timeout=3000):
        dbconnmanager.connect_to_db(dbaccessor)
    assert dbconnmanager.is_connected()
    qtbot.wait(1000)

    return mainwindow


# =============================================================================
# ---- Tests
# =============================================================================
def test_construction_log_tool(mainwindow, constructlog, qtbot, mocker):
    """
    Test that the tool to add, show and delete construction logs
    is working as expected.
    """
    # Make sure the obervation wells table is visible.
    tabwidget = mainwindow.plugin.tabwidget
    tabwidget.setCurrentIndex(0)
    qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)

    table = mainwindow.plugin.current_table()
    assert table.get_table_id() == 'table_observation_wells'
    assert len(table.model().libraries['stations_with_construction_log']) == 0

    # Select the second cell of the table.
    model_index = table.model().index(1, 0)
    selection_model = table.tableview.selectionModel()
    selection_model.setCurrentIndex(model_index, selection_model.Current)

    # Make sure the state of the construction log menu is as expected.
    # Note that we need to show the menu to trigger an update of its state.
    pos = table.construction_log_btn.mapToGlobal(QPoint(0, 0))
    table.construction_log_btn.menu().popup(pos)
    assert table.attach_construction_log_action.isEnabled()
    assert not table.show_construction_log_action.isEnabled()
    assert not table.remove_construction_log_action.isEnabled()

    # Attach a construction log to the currently selected piezometric station.
    mocker.patch.object(
        QFileDialog, 'getOpenFileName', return_value=(constructlog, None))
    with qtbot.waitSignal(table.sig_construction_log_attached):
        table.attach_construction_log_action.trigger()
    qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)
    assert len(table.model().libraries['stations_with_construction_log']) == 1

    pos = table.construction_log_btn.mapToGlobal(QPoint(0, 0))
    table.construction_log_btn.menu().popup(pos)
    assert table.attach_construction_log_action.isEnabled()
    assert table.show_construction_log_action.isEnabled()
    assert table.remove_construction_log_action.isEnabled()

    # Show the newly added construction log in an external application.
    mocker.patch('os.startfile')
    with qtbot.waitSignal(table.sig_construction_log_shown):
        table.show_construction_log_action.trigger()

    # Delete the newly added construction log from the database.
    with qtbot.waitSignal(table.sig_construction_log_removed):
        table.remove_construction_log_action.trigger()
    qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)
    assert len(table.model().libraries['stations_with_construction_log']) == 0

    pos = table.construction_log_btn.mapToGlobal(QPoint(0, 0))
    table.construction_log_btn.menu().popup(pos)
    assert table.attach_construction_log_action.isEnabled()
    assert not table.show_construction_log_action.isEnabled()
    assert not table.remove_construction_log_action.isEnabled()


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
