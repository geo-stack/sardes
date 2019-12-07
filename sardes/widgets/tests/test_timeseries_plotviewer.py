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

# ---- Third party imports
import pytest
from qtpy.QtCore import Qt

# ---- Local imports
from sardes.database.accessor_demo import DatabaseAccessorDemo
from sardes.widgets.timeseries import TimeSeriesPlotViewer


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dbaccessor():
    dbaccessor = DatabaseAccessorDemo()
    return dbaccessor


@pytest.fixture
def tseriesviewer(qtbot, dbaccessor):
    viewer = TimeSeriesPlotViewer()

    wlevel_tseries = dbaccessor.get_timeseries_for_obs_well('', 'NIV_EAU')
    viewer.create_axe(wlevel_tseries)

    wtemp_tseries = dbaccessor.get_timeseries_for_obs_well('', 'TEMP_EAU')
    viewer.create_axe(wtemp_tseries)

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

    assert current_axe_button.checked_action().data() == tseries_axes_list[1]
    assert (tseries_axes_list[1].get_zorder() >
            tseries_axes_list[0].get_zorder())

    # Select the first axes as current.
    current_axe_menu = current_axe_button.menu()
    current_axe_menu.show()

    action = current_axe_menu.actions()[0]
    with qtbot.waitSignal(current_axe_button.sig_checked_action_changed):
        qtbot.mouseClick(
            current_axe_menu,
            Qt.LeftButton,
            pos=current_axe_menu.actionGeometry(action).center())

    assert (current_axe_button.checked_action().data() == tseries_axes_list[0])
    assert (tseries_axes_list[0].get_zorder() >
            tseries_axes_list[1].get_zorder())


def test_tseriesviewer_axes_visibility(tseriesviewer, qtbot):
    """
    Test that changing the axes visibility is working as expected.
    """
    tseries_axes_list = tseriesviewer.canvas.figure.tseries_axes_list
    visible_axes_button = tseriesviewer.visible_axes_button

    # Assert that all the axes are visible.
    assert tseries_axes_list[0].get_visible()
    assert tseries_axes_list[1].get_visible()

    # Hide the second axes (the one currently selected).
    qtbot.mouseClick(visible_axes_button, Qt.LeftButton)
    assert tseries_axes_list[0].get_visible()
    assert not tseries_axes_list[1].get_visible()

    # Seclect the first axes and hide it.
    tseriesviewer.current_axe_button.menu().actions()[0].toggle()
    qtbot.mouseClick(visible_axes_button, Qt.LeftButton)
    assert not tseries_axes_list[0].get_visible()
    assert not tseries_axes_list[1].get_visible()

    # Seclect the second axes and show it again.
    tseriesviewer.current_axe_button.menu().actions()[1].toggle()
    qtbot.mouseClick(visible_axes_button, Qt.LeftButton)
    assert not tseries_axes_list[0].get_visible()
    assert tseries_axes_list[1].get_visible()


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw', '-s'])
