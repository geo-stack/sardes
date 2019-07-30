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

# ---- Local imports
from sardes.database.database_manager import DatabaseConnectionManager
from sardes.database.accessor_demo import OBS_WELLS_DF, DatabaseAccessorDemo
from sardes.widgets.locationtable import ObservationWellTableView


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
    assert_frame_equal(obs_well_tableview.obs_well_table_model.obs_wells,
                       OBS_WELLS_DF)


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw', '-s'])
