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
import matplotlib.pyplot as plt
import pandas as pd
import pytest
from qtpy.QtCore import Qt, QPoint
from qtpy.QtWidgets import QMainWindow, QFileDialog

# ---- Local imports
from sardes.database.database_manager import DatabaseConnectionManager
from sardes.plugins.tables import SARDES_PLUGIN_CLASS
from sardes.widgets.tableviews import MSEC_MIN_PROGRESS_DISPLAY
from sardes.database.accessors.accessor_sardes_lite import (
    DatabaseAccessorSardesLite)


OBS_WELLS_DF = pd.DataFrame(
    [['03037041', "St-Paul-d'Abbotsford", "Saint-Paul-d'Abbotsford",
      'MT', 'Confined', 3, 'No', 'No', 45.445178, -72.828773, True, None],
     ['02200001', "Réserve de Duchénier", "Saint-Narcisse-de-Rimouski",
      'ROC', 'Unconfined', 2, 'Yes', 'No', 48.20282, -68.52795, True, None],
     ['02167001', 'Matane', 'Matane',
      'MT', 'Captive', 3, 'No', 'Yes', 48.81151, -67.53562, True, None],
     ['02600001', "L'Islet", "L'Islet",
      'ROC', 'Unconfined', 2, 'Yes', 'No', 47.093526, -70.338989, True, None],
     ['03040002', 'PO-01', 'Calixa-Lavallée',
      'ROC', 'Confined', 1, 'No', 'No', 45.74581, -73.28024, True, None]],
    columns=['obs_well_id', 'common_name', 'municipality',
             'aquifer_type', 'confinement', 'aquifer_code',
             'in_recharge_zone', 'is_influenced', 'latitude',
             'longitude', 'is_station_active', 'obs_well_notes'])


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dbaccessor(tmp_path):
    dbaccessor = DatabaseAccessorSardesLite(
        osp.join(tmp_path, 'sqlite_database_test.db'))
    dbaccessor.init_database()

    # Add observation wells to the database.
    for index, row in OBS_WELLS_DF.iterrows():
        sampling_feature_uuid = dbaccessor._create_index(
            'observation_wells_data')
        dbaccessor.add_observation_wells_data(
            sampling_feature_uuid,
            attribute_values=row.to_dict())
    return dbaccessor


@pytest.fixture
def constructlog(tmp_path):
    # Create a dummy construction log file.
    filename = osp.join(tmp_path, 'test_construction_log.pdf')
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3, 4])
    fig.savefig(filename)
    return filename


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
