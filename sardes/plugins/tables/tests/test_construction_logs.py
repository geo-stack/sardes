# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the station construction log tool.
"""

# ---- Standard imports
import os
import os.path as osp
from unittest.mock import Mock
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pytest
from qtpy.QtCore import QPoint
from qtpy.QtWidgets import QFileDialog

# ---- Local imports
from sardes.app.mainwindow import MainWindowBase
from sardes.plugins.tables import SARDES_PLUGIN_CLASS
from sardes.widgets.tableviews import MSEC_MIN_PROGRESS_DISPLAY
from sardes.database.accessors import DatabaseAccessorSardesLite


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
def mainwindow(qtbot, mocker, dbaccessor):
    class MainWindow(MainWindowBase):
        def __init__(self):
            super().__init__()

        def setup_internal_plugins(self):
            self.view_timeseries_data = Mock()
            self.plugin = SARDES_PLUGIN_CLASS(self)
            self.plugin.register_plugin()

    mainwindow = MainWindow()
    mainwindow.show()
    qtbot.waitExposed(mainwindow)

    dbconnmanager = mainwindow.db_connection_manager
    with qtbot.waitSignal(dbconnmanager.sig_database_connected, timeout=3000):
        dbconnmanager.connect_to_db(dbaccessor)
    assert dbconnmanager.is_connected()
    qtbot.wait(150)

    yield mainwindow

    # We need to wait for the mainwindow to close properly to avoid
    # runtime errors on the c++ side.
    with qtbot.waitSignal(mainwindow.sig_about_to_close):
        mainwindow.close()


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
    constructlogs_manager = table.construction_logs_manager
    assert table.get_table_id() == 'table_observation_wells'
    assert len(table.model().libraries['stored_attachments_info']) == 0

    # Select the second cell of the table.
    model_index = table.model().index(1, 0)
    selection_model = table.tableview.selectionModel()
    selection_model.setCurrentIndex(model_index, selection_model.Current)

    # Make sure the state of the construction log menu is as expected.
    # Note that we need to show the menu to trigger an update of its state.
    pos = constructlogs_manager.toolbutton.mapToGlobal(QPoint(0, 0))
    constructlogs_manager.toolbutton.menu().popup(pos)
    assert constructlogs_manager.attach_action.isEnabled()
    assert not constructlogs_manager.show_action.isEnabled()
    assert not constructlogs_manager.remove_action.isEnabled()

    # Attach a construction log to the currently selected piezometric station.
    mocker.patch.object(
        QFileDialog, 'getOpenFileName', return_value=(constructlog, None))
    with qtbot.waitSignal(constructlogs_manager.sig_attachment_added):
        constructlogs_manager.attach_action.trigger()
    qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)
    assert len(table.model().libraries['stored_attachments_info']) == 1

    pos = constructlogs_manager.toolbutton.mapToGlobal(QPoint(0, 0))
    constructlogs_manager.toolbutton.menu().popup(pos)
    assert constructlogs_manager.attach_action.isEnabled()
    assert constructlogs_manager.show_action.isEnabled()
    assert constructlogs_manager.remove_action.isEnabled()

    # Show the newly added construction log in an external application.
    mocker.patch('os.startfile')
    with qtbot.waitSignal(constructlogs_manager.sig_attachment_shown):
        constructlogs_manager.show_action.trigger()

    # Delete the newly added construction log from the database.
    with qtbot.waitSignal(constructlogs_manager.sig_attachment_removed):
        constructlogs_manager.remove_action.trigger()
    qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)
    assert len(table.model().libraries['stored_attachments_info']) == 0

    pos = constructlogs_manager.toolbutton.mapToGlobal(QPoint(0, 0))
    constructlogs_manager.toolbutton.menu().popup(pos)
    assert constructlogs_manager.attach_action.isEnabled()
    assert not constructlogs_manager.show_action.isEnabled()
    assert not constructlogs_manager.remove_action.isEnabled()
    constructlogs_manager.toolbutton.menu().close()


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
