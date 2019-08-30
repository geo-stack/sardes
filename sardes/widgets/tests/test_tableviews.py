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
from unittest.mock import Mock

# ---- Third party imports
import pytest
from pandas.testing import assert_frame_equal
from qtpy.QtCore import Qt

# ---- Local imports
from sardes.database.database_manager import DatabaseConnectionManager
from sardes.database.accessor_demo import OBS_WELLS_DF, DatabaseAccessorDemo
from sardes.widgets.tableviews import ObservationWellTableView


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dbconnmanager():
    dbconnmanager = DatabaseConnectionManager()
    return dbconnmanager


@pytest.fixture
def dbaccessor():
    dbaccessor = DatabaseAccessorDemo()
    return dbaccessor


@pytest.fixture
def obs_well_tableview(qtbot, mocker, dbconnmanager):
    obs_well_tableview = ObservationWellTableView(dbconnmanager)
    obs_well_tableview.show()
    qtbot.waitForWindowShown(obs_well_tableview)
    qtbot.addWidget(obs_well_tableview)

    # Setup the column options button.
    column_options_button = obs_well_tableview.get_column_options_button()
    qtbot.addWidget(column_options_button)

    return obs_well_tableview


# =============================================================================
# ---- Tests for ObservationWellTableView
# =============================================================================
def test_obs_well_tableview_init(obs_well_tableview, dbaccessor,
                                 mocker, qtbot):
    """Test that the location table view is initialized correctly."""
    assert obs_well_tableview
    assert obs_well_tableview.model().rowCount() == 0

    # Connect to the database. This should trigger in the location table view
    # a query to get and display the content of the database location table.
    obs_well_tableview.db_connection_manager.connect_to_db(dbaccessor)

    # We need to wait a little to let the time for the data to display in
    # the table.
    qtbot.wait(3000)

    assert obs_well_tableview.model().rowCount() == len(OBS_WELLS_DF)
    assert_frame_equal(obs_well_tableview.model.dataf, OBS_WELLS_DF)

    # Assert that all columns are visible.
    for action in obs_well_tableview._toggle_column_visibility_actions:
        assert action.isChecked()
    for logical_index in range(obs_well_tableview.column_count()):
        assert (not obs_well_tableview
                .horizontalHeader()
                .isSectionHidden(logical_index))


def test_toggle_column_visibility(obs_well_tableview, qtbot):
    """Test toggling on and off the visibility of the columns."""
    horiz_header = obs_well_tableview.horizontalHeader()

    # Hide the second, third, and fourth columns of the table.
    for logical_index in [1, 2, 3]:
        action = (obs_well_tableview
                  ._toggle_column_visibility_actions[logical_index])
        action.toggle()

        assert not action.isChecked()
        assert horiz_header.isSectionHidden(logical_index)

    # Toggle back the visibility of the second column.
    action = obs_well_tableview._toggle_column_visibility_actions[1]
    action.toggle()
    assert action.isChecked()
    assert not horiz_header.isSectionHidden(1)

    # Restore column visibility with action 'Show all'.
    menu = obs_well_tableview.get_column_options_button().menu()
    menu.actions()[1].trigger()
    for action in obs_well_tableview._toggle_column_visibility_actions:
        assert action.isChecked()
    for logical_index in range(obs_well_tableview.column_count()):
        assert not horiz_header.isSectionHidden(logical_index)


def test_restore_columns_to_defaults(obs_well_tableview, qtbot):
    """Test restoring the visibility and order of the columns."""
    horiz_header = obs_well_tableview.horizontalHeader()

    # Move the third column to first position.
    horiz_header.moveSection(2, 0)
    assert horiz_header.logicalIndex(0) == 2
    assert horiz_header.logicalIndex(2) == 1

    # Hide the second column.
    logical_index = 1
    action = (obs_well_tableview
              ._toggle_column_visibility_actions[logical_index])
    action.toggle()
    assert not action.isChecked()
    assert horiz_header.isSectionHidden(logical_index)

    # Restore columns to defaults with action 'Restore to defaults'.
    menu = obs_well_tableview.get_column_options_button().menu()
    menu.actions()[0].trigger()
    assert horiz_header.logicalIndex(0) == 0
    assert horiz_header.logicalIndex(2) == 2
    assert action.isChecked()
    assert not horiz_header.isSectionHidden(logical_index)


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw', '-s'])
