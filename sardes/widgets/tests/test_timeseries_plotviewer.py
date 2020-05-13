# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the ObservationWellTableView.
"""

# ---- Standard imports
import os.path as osp
import sys

# ---- Third party imports
import pytest
from qtpy.QtCore import Qt

# ---- Local imports
from sardes.widgets.timeseries import TimeSeriesPlotViewer
from sardes.api.timeseries import DataType
from sardes.database.database_manager import DatabaseConnectionManager


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dbaccessor():
    # We need to do this to make sure the demo database is reinitialized
    # after each test.
    try:
        del sys.modules['sardes.database.accessor_demo']
    except KeyError:
        pass
    from sardes.database.accessor_demo import DatabaseAccessorDemo
    return DatabaseAccessorDemo()


@pytest.fixture
def dbconnmanager(qtbot, dbaccessor):
    dbconnmanager = DatabaseConnectionManager()
    with qtbot.waitSignal(dbconnmanager.sig_database_connected, timeout=3000):
        dbconnmanager.connect_to_db(dbaccessor)
    assert dbconnmanager.is_connected()
    qtbot.wait(100)
    return dbconnmanager


@pytest.fixture
def tseriesviewer(qtbot, dbconnmanager):
    viewer = TimeSeriesPlotViewer()

    tseries_data = dbconnmanager.get_timeseries_for_obs_well(
        1, [DataType.WaterLevel, DataType.WaterTemp], main_thread=True)
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


def test_manual_measurements(tseriesviewer, qtbot, dbaccessor):
    """
    Test that setting manual measurements for a give datatype is working
    as expected.
    """
    axe = tseriesviewer.figure.tseries_axes_list[0]
    assert axe._mpl_artist_handles['manual_measurements'] is None
    assert len(tseriesviewer.figure.base_axes.get_legend().legendHandles) == 2

    # Fetch the manual measurements for a given well from the database.
    measurements = dbaccessor.get_manual_measurements()
    measurements = measurements[measurements['sampling_feature_uuid'] == 1]
    assert len(measurements) == 1

    # Set the manual measurement in the plot viewer.
    tseriesviewer.set_manual_measurements(
        DataType.WaterLevel, measurements[['datetime', 'value']])
    assert axe._mpl_artist_handles['manual_measurements'] is not None
    assert len(axe._mpl_artist_handles['manual_measurements'].get_xdata()) == 1

    # Assert that the legend was updated as expected.
    assert len(tseriesviewer.figure.base_axes.get_legend().legendHandles) == 3


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
