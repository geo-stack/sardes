# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the TimeSeriesPlotViewer.
"""

# ---- Standard imports
import os.path as osp

# ---- Third party imports
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QMessageBox

# ---- Local imports
from sardes.widgets.timeseries import TimeSeriesPlotViewer
from sardes.api.timeseries import DataType
from sardes.database.database_manager import DatabaseConnectionManager
from sardes.database.accessors import DatabaseAccessorSardesLite


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
def dbconnmanager(qtbot, dbaccessor):
    dbconnmanager = DatabaseConnectionManager()
    with qtbot.waitSignal(dbconnmanager.sig_database_connected, timeout=3000):
        dbconnmanager.connect_to_db(dbaccessor)
    assert dbconnmanager.is_connected()
    qtbot.wait(100)
    return dbconnmanager


@pytest.fixture
def obs_well_uuid(obswells_data):
    return obswells_data.index[0]


@pytest.fixture
def tseriesviewer(qtbot, dbconnmanager, obs_well_uuid):
    viewer = TimeSeriesPlotViewer()

    tseries_data = dbconnmanager.get_timeseries_for_obs_well(
        obs_well_uuid,
        data_types=[DataType.WaterLevel, DataType.WaterTemp],
        main_thread=True)
    viewer.set_data(tseries_data)

    qtbot.addWidget(viewer)
    viewer.show()
    return viewer


# =============================================================================
# ---- Tests for the TimeSeriesPlotViewer
# =============================================================================
def test_tseriesviewer_init(tseriesviewer):
    """Test that the timeseries plot viewer is initialized correctly."""
    assert tseriesviewer
    assert len(tseriesviewer.canvas.figure.tseries_axes_list) == 2


def test_tseriesviewer_current_axes(tseriesviewer, qtbot):
    """
    Test that changing the current axes with the current axes button in
    the timeseries plot viewer toolbar is working as expected.
    """
    tseries_axes_list = tseriesviewer.canvas.figure.tseries_axes_list
    current_axe_button = tseriesviewer.current_axe_button

    assert current_axe_button.checked_action().data() == tseries_axes_list[0]
    assert (tseries_axes_list[0].get_zorder() >
            tseries_axes_list[1].get_zorder())

    # Select the second axes as current.
    current_axe_menu = current_axe_button.menu()
    current_axe_menu.show()

    action = current_axe_menu.actions()[1]
    with qtbot.waitSignal(current_axe_button.sig_checked_action_changed):
        qtbot.mouseClick(
            current_axe_menu,
            Qt.LeftButton,
            pos=current_axe_menu.actionGeometry(action).center())

    assert (current_axe_button.checked_action().data() == tseries_axes_list[1])
    assert (tseries_axes_list[1].get_zorder() >
            tseries_axes_list[0].get_zorder())


def test_tseriesviewer_axes_visibility(tseriesviewer, qtbot):
    """
    Test that changing the axes visibility is working as expected.
    """
    tseries_axes_list = tseriesviewer.figure.tseries_axes_list

    # Assert that all the axes are visible.
    assert tseries_axes_list[0].get_visible()
    assert tseries_axes_list[1].get_visible()
    assert len(tseriesviewer.figure.base_axes.get_legend().legendHandles) == 2
    assert tseriesviewer.figure.base_axes.get_legend().get_visible() is True

    # Hide the second axes.
    tseriesviewer.visible_axes_btn.menu().actions()[1].toggle()
    assert tseries_axes_list[0].get_visible()
    assert not tseries_axes_list[1].get_visible()
    assert len(tseriesviewer.figure.base_axes.get_legend().legendHandles) == 1
    assert tseriesviewer.figure.base_axes.get_legend().get_visible() is True

    # Hide the first axes.
    tseriesviewer.visible_axes_btn.menu().actions()[0].toggle()
    assert not tseries_axes_list[0].get_visible()
    assert not tseries_axes_list[1].get_visible()
    assert len(tseriesviewer.figure.base_axes.get_legend().legendHandles) == 0
    assert tseriesviewer.figure.base_axes.get_legend().get_visible() is False

    # Show the second axes again.
    tseriesviewer.visible_axes_btn.menu().actions()[1].toggle()
    assert not tseries_axes_list[0].get_visible()
    assert tseries_axes_list[1].get_visible()
    assert len(tseriesviewer.figure.base_axes.get_legend().legendHandles) == 1
    assert tseriesviewer.figure.base_axes.get_legend().get_visible() is True


def test_manual_measurements(tseriesviewer, qtbot, dbaccessor, obs_well_uuid):
    """
    Test that setting manual measurements for a give datatype is working
    as expected.
    """
    axe = tseriesviewer.figure.tseries_axes_list[0]
    assert axe._mpl_artist_handles['manual_measurements'] is None
    assert len(tseriesviewer.figure.base_axes.get_legend().legendHandles) == 2

    # Fetch the manual measurements for a given well from the database.
    measurements = dbaccessor.get('manual_measurements')
    measurements = measurements[
        measurements['sampling_feature_uuid'] == obs_well_uuid]
    assert len(measurements) == 3

    # Set the manual measurement in the plot viewer.
    tseriesviewer.set_manual_measurements(
        DataType.WaterLevel, measurements[['datetime', 'value']])
    assert axe._mpl_artist_handles['manual_measurements'] is not None
    assert len(axe._mpl_artist_handles['manual_measurements'].get_xdata()) == 3

    # Assert that the legend was updated as expected.
    assert len(tseriesviewer.figure.base_axes.get_legend().legendHandles) == 3


def test_linewidth_markersize_option(tseriesviewer):
    """
    Test that the options to change the line width and marker size of the
    plot of the currently selected timeseries is working as expected.
    """
    current_axe = tseriesviewer.current_axe()
    assert tseriesviewer.fmt_line_weight.value() == 0.75
    assert tseriesviewer.fmt_marker_size.value() == 0
    assert current_axe._linewidth == 0.75
    assert current_axe._markersize == 0
    assert len(current_axe._mpl_artist_handles['data'])
    for artist in current_axe._mpl_artist_handles['data'].values():
        assert artist.get_linewidth() == 0.75
        assert artist.get_markersize() == 0

    # Change the line width and marker size of the current axe.
    tseriesviewer.fmt_line_weight.setValue(1)
    tseriesviewer.fmt_marker_size.setValue(2)
    assert current_axe._linewidth == 1
    assert current_axe._markersize == 2
    assert len(current_axe._mpl_artist_handles['data'])
    for artist in current_axe._mpl_artist_handles['data'].values():
        assert artist.get_linewidth() == 1
        assert artist.get_markersize() == 2

    # Change the current axe to the water temperature axe.
    tseriesviewer.set_current_axe(1)
    current_axe = tseriesviewer.current_axe()
    assert tseriesviewer.fmt_line_weight.value() == 0.75
    assert tseriesviewer.fmt_marker_size.value() == 0
    assert current_axe._linewidth == 0.75
    assert current_axe._markersize == 0
    assert len(current_axe._mpl_artist_handles['data'])
    for artist in current_axe._mpl_artist_handles['data'].values():
        assert artist.get_linewidth() == 0.75
        assert artist.get_markersize() == 0

    # Go back to the water level axe.
    tseriesviewer.set_current_axe(0)
    current_axe = tseriesviewer.current_axe()
    assert tseriesviewer.fmt_line_weight.value() == 1
    assert tseriesviewer.fmt_marker_size.value() == 2
    assert current_axe._linewidth == 1
    assert current_axe._markersize == 2
    assert len(current_axe._mpl_artist_handles['data'])
    for artist in current_axe._mpl_artist_handles['data'].values():
        assert artist.get_linewidth() == 1
        assert artist.get_markersize() == 2


def test_save_tseries_plot(tseriesviewer, mocker, tmp_path, qtbot):
    """
    Test that saving plots to different file formats is working as
    expected.
    """
    qmsgbox_patcher = mocker.patch.object(
        QMessageBox, 'critical', return_value=QMessageBox.Ok)
    for fext in ['.png', '.jpg', '.svg', '.pdf', '.ps', '.eps']:
        fpath = osp.join(tmp_path, 'test_figure' + fext)
        mocker.patch('matplotlib.backends.qt_compat._getSaveFileName',
                     return_value=(fpath, fext))
        qtbot.mouseClick(tseriesviewer.save_figure_button, Qt.LeftButton)
        assert osp.exists(fpath)
    assert qmsgbox_patcher.call_count == 0


def test_copy_tseries_plot_to_clipboard(tseriesviewer, mocker, qtbot):
    """
    Test that copying the timeseries plot to the clipboard is working as
    expected.
    """
    QApplication.clipboard().clear()
    assert QApplication.clipboard().image().isNull()

    qtbot.mouseClick(tseriesviewer.copy_to_clipboard_btn, Qt.LeftButton)
    assert not QApplication.clipboard().image().isNull()


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
