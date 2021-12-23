# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the Readings plugin.
"""

# ---- Standard imports
import os
import os.path as osp
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pytest

# ---- Local imports
from sardes.api.timeseries import DataType
from sardes.database.database_manager import DatabaseConnectionManager
from sardes.plugins.readings import SARDES_PLUGIN_CLASS
from sardes.widgets.tableviews import QMessageBox
from sardes.database.accessors import DatabaseAccessorSardesLite
from sardes.database.accessors.accessor_helpers import init_tseries_edits
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
def dbconnmanager(qtbot):
    dbconnmanager = DatabaseConnectionManager()
    return dbconnmanager


@pytest.fixture
def obswell_uuid(obswells_data):
    return obswells_data.index[0]


@pytest.fixture
def mainwindow(qtbot, mocker, dbconnmanager, dbaccessor, obswell_uuid,
               readings_data):
    class MainWindowMock(MainWindowBase):
        def __init__(self):
            super().__init__()

        def setup_internal_plugins(self):
            self.plugin = SARDES_PLUGIN_CLASS(self)
            self.plugin.register_plugin()
            self.internal_plugins.append(self.plugin)

    mainwindow = MainWindowMock()
    mainwindow.resize(1200, 750)
    mainwindow.show()
    qtbot.waitExposed(mainwindow)

    dbconnmanager = mainwindow.db_connection_manager
    with qtbot.waitSignal(dbconnmanager.sig_database_connected, timeout=3000):
        dbconnmanager.connect_to_db(dbaccessor)
    assert dbconnmanager.is_connected()
    qtbot.wait(150)

    # Show data for observation well #1.
    mainwindow.plugin.view_timeseries_data(obswell_uuid)
    qtbot.waitUntil(lambda: len(mainwindow.plugin._tseries_table_widgets) == 1)

    # Wait until the data are loaded in the table.
    table = mainwindow.plugin._tseries_table_widgets[obswell_uuid]
    qtbot.waitUntil(lambda: table.tableview.row_count() == len(readings_data))
    assert table.isVisible()
    assert not table.model()._repere_data.empty
    assert (table.model().manual_measurements()['value'].values.tolist() ==
            [5.23, 4.36, 4.91])

    yield mainwindow

    # We need to wait for the mainwindow to close properly to avoid
    # runtime errors on the c++ side.
    with qtbot.waitSignal(mainwindow.sig_about_to_close):
        mainwindow.close()

    for table in mainwindow.plugin._tseries_table_widgets.values():
        assert not table.isVisible()
        assert table.plot_viewer is None


# =============================================================================
# ---- Tests
# =============================================================================
def test_plot_viewer(mainwindow, qtbot, obswell_uuid, readings_data):
    """
    Test that plotting the monitoring data is working as expected.
    """
    table = mainwindow.plugin._tseries_table_widgets[obswell_uuid]
    assert table.plot_viewer is None

    # Test that the plot viewer is created as expected.
    table.plot_readings()
    qtbot.waitExposed(table.plot_viewer)
    assert (table.plot_viewer.windowTitle() ==
            "03037041 - St-Paul-d'Abbotsford (Saint-Paul-d'Abbotsford)")

    # Assert that the axes were created as expected.
    assert len(table.plot_viewer.canvas.figure.tseries_axes_list) == 3
    ax_wlvl = table.plot_viewer.canvas.figure.tseries_axes_list[0]
    assert ax_wlvl.tseries_group.data_type == DataType.WaterLevel
    ax_wtemp = table.plot_viewer.canvas.figure.tseries_axes_list[1]
    assert ax_wtemp.tseries_group.data_type == DataType.WaterTemp
    ax_wec = table.plot_viewer.canvas.figure.tseries_axes_list[2]
    assert ax_wec.tseries_group.data_type == DataType.WaterEC

    # Assert that the manual measurements were plotted as expected.
    artist = ax_wlvl._mpl_artist_handles['manual_measurements']
    assert (list(artist.get_ydata()) == [5.23, 4.36, 4.91])

    # Assert that the monitoring data were plotted as expected.
    obs_id = table.model().dataf['obs_id'].unique()[0]
    artist = ax_wlvl._mpl_artist_handles['data'][obs_id]
    assert (list(artist.get_ydata()) ==
            readings_data[DataType.WaterLevel].values.tolist())


def test_plot_viewer_update(mainwindow, qtbot, obswell_uuid):
    """
    Test that the plot viewer is updated as expected when the monitoring data
    and metadata of the observation well are modified.
    """
    table = mainwindow.plugin._tseries_table_widgets[obswell_uuid]
    dbconnmanager = mainwindow.db_connection_manager

    assert table.plot_viewer is None
    table.plot_readings()
    qtbot.waitExposed(table.plot_viewer)

    # Test that a change in the observation well data is reflected as
    # expected in the plot viewer.
    with qtbot.waitSignal(dbconnmanager.sig_database_data_changed):
        dbconnmanager.set(
            'observation_wells_data',
            obswell_uuid,
            {'obs_well_id': '12345',
             'common_name': 'well_common_name',
             'municipality': 'well_municipality'})
    expected_win_title = "12345 - well_common_name (well_municipality)"
    qtbot.waitUntil(
        lambda: table.plot_viewer.windowTitle() == expected_win_title)

    # Test that a change in the manual measurements is reflected as
    # expected in the plot viewer.
    with qtbot.waitSignal(dbconnmanager.sig_database_data_changed):
        dbconnmanager.set(
            'manual_measurements',
            table.model().manual_measurements().index[0],
            {'value': 1.5678})

    ax_wlvl = table.plot_viewer.canvas.figure.tseries_axes_list[0]
    artist = ax_wlvl._mpl_artist_handles['manual_measurements']
    qtbot.waitUntil(lambda: list(artist.get_ydata()) == [1.5678, 4.36, 4.91])

    # Test that a change in the readings data is reflected as
    # expected in the plot viewer.
    with qtbot.waitSignal(dbconnmanager.sig_tseries_data_changed):
        tseries_edits = init_tseries_edits()
        tseries_edits.loc[
            (table.model().dataf['datetime'].iloc[0],
             table.model().dataf['obs_id'].iloc[0],
             DataType.WaterLevel),
            'value'] = 103.25
        dbconnmanager.save_timeseries_data_edits(
            tseries_edits, obswell_uuid)
    qtbot.wait(300)

    obs_id = table.model().dataf['obs_id'].unique()[0]
    ax_wlvl = table.plot_viewer.canvas.figure.tseries_axes_list[0]
    artist_wlvl = ax_wlvl._mpl_artist_handles['data'][obs_id]
    qtbot.waitUntil(lambda: artist_wlvl.get_ydata()[0] == 103.25)

    # We still need to assert that the manual measurements were not cleared
    # in the process. See cgq-qgc/sardes#409.
    artist_measurements_ = ax_wlvl._mpl_artist_handles['manual_measurements']
    assert (list(artist_measurements_.get_ydata()) == [1.5678, 4.36, 4.91])


def test_delete_timeseries_data(mainwindow, qtbot, mocker, obswell_uuid,
                                readings_data):
    """
    Test that deleting data in a timeseries data table is working as
    expected.

    Regression test for cgq-qgc/sardes#210
    """
    table = mainwindow.plugin._tseries_table_widgets[obswell_uuid]

    # Select one row in the table.
    model = table.model()
    selection_model = table.tableview.selectionModel()
    selection_model.setCurrentIndex(
        model.index(3, 0), selection_model.SelectCurrent)
    assert table.tableview.get_rows_intersecting_selection() == [3]
    assert table.tableview.delete_row_action.isEnabled()

    # Delete the selected row.
    table.tableview.delete_row_action.trigger()
    assert table.tableview.model().data_edit_count() == 1
    assert model.has_unsaved_data_edits() is True

    # Select more rows in the table.
    selection_model.select(model.index(1, 1), selection_model.Select)
    selection_model.select(model.index(4, 1), selection_model.Select)
    selection_model.select(model.index(5, 1), selection_model.Select)
    assert table.tableview.get_rows_intersecting_selection() == [1, 3, 4, 5]

    # Delete the selected rows.
    table.tableview.delete_row_action.trigger()
    assert model.data_edit_count() == 2
    assert model.has_unsaved_data_edits() is True

    # Commit the row deletions to the database.
    mocker.patch.object(QMessageBox, 'exec_', return_value=QMessageBox.Save)
    with qtbot.waitSignal(model.sig_data_updated, timeout=3000):
        table.tableview.save_edits_action.trigger()
    assert model.data_edit_count() == 0
    assert model.has_unsaved_data_edits() is False
    assert table.tableview.row_count() == len(readings_data) - 4

    # Close the timeseries table.
    mainwindow.plugin.tabwidget.tabCloseRequested.emit(0)
    qtbot.waitUntil(lambda: len(mainwindow.plugin._tseries_table_widgets) == 0)


def test_edit_then_delete_row(mainwindow, qtbot, mocker, obswell_uuid,
                              readings_data):
    """
    Test that editing and then deleting data on a same row is working as
    expected.

    Regression test for cgq-qgc/sardes#337
    """
    table = mainwindow.plugin._tseries_table_widgets[obswell_uuid]

    # Edit the water level value on the second row of the table.
    expected_value = readings_data.iloc[2][DataType.WaterLevel]
    model_index = table.model().index(2, 2)
    assert table.model().get_value_at(model_index) == expected_value
    edited_value = 999.99
    table.model().set_data_edit_at(model_index, edited_value)
    assert table.model().get_value_at(model_index) == 999.99
    assert table.model().data_edit_count() == 1

    # Delete the second row of the table.
    table.model().delete_row([2])
    assert table.model().data_edit_count() == 2

    # Commit the edits to the database.
    mocker.patch.object(QMessageBox, 'exec_', return_value=QMessageBox.Save)
    with qtbot.waitSignal(table.model().sig_data_updated, timeout=3000):
        table.tableview.save_edits_action.trigger()

    # Note: the data on the second row corresponds to the data that was
    # previously on the third row in the original dataset.
    expected_value = readings_data.iloc[2 + 1][DataType.WaterLevel]
    model_index = table.model().index(2, 2)
    assert table.model().get_value_at(model_index) == expected_value

    assert table.tableview.row_count() == len(readings_data) - 1


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
