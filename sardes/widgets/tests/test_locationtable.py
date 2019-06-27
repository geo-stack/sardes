# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the LocationTableView.
"""

# ---- Standard imports
from collections import namedtuple
import os.path as osp
from unittest.mock import Mock

# ---- Third party imports
import pytest

# ---- Local imports
from sardes.database.manager import DatabaseConnectionManager, DataAccessor
from sardes.widgets.locationtable import LocationTableView
from sardes.database.accessor_pg import LOCTABLEATTRS


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dbconnmanager():
    dbconnmanager = DatabaseConnectionManager()
    return dbconnmanager


@pytest.fixture
def locationtableview(qtbot, mocker, dbconnmanager):
    locationtableview = LocationTableView(dbconnmanager)
    # qtbot.addWidget(locationtableview)
    locationtableview.show()
    qtbot.waitForWindowShown(locationtableview)
    return locationtableview


@pytest.fixture
def locations():
    """
    Return a list named tuple location that mimick the structure of the
    location table in the database.
    """
    Location = namedtuple('Location', ' '.join(LOCTABLEATTRS))
    locations = []
    for i in range(3):
        locations.append(
            Location(no_piezometre='no_piezometre#{}'.format(i),
                     nom_communn='nom_communn#{}'.format(i),
                     municipalite='municipalite#{}'.format(i),
                     aquifere='aquifere#{}'.format(i),
                     nappe='nappe#{}'.format(i),
                     code_aqui=i,
                     zone_rechar='zone_rechar#{}'.format(i),
                     influences='influences#{}'.format(i),
                     latitude_8=45 + i/10,
                     longitude=-75 + i/10,
                     station_active='station_active#{}'.format(i),
                     remarque='remarque#{}'.format(i),
                     loc_id='loc_id#{}'.format(i),
                     geom='geom#{}'.format(i),
                     )
            )
    return locations


# =============================================================================
# ---- Tests for LocationTableView
# =============================================================================
def test_locationtableview_init(locationtableview, locations, mocker,
                                qtbot):
    """Test that the location table view is initialized correctly."""
    assert locationtableview
    assert locationtableview.model().rowCount() == 0

    # Connect to the database. This should trigger in the location table view
    # a query to get and display the content of the database location table.

    mocked_connection = Mock()
    mocked_connection.closed = False
    mocker.patch('sqlalchemy.engine.Engine.connect',
                 return_value=mocked_connection)
    mocker.patch.object(DataAccessor, 'get_locations', return_value=locations)

    dbconnmanager = locationtableview.db_connection_manager
    with qtbot.waitSignal(dbconnmanager.sig_database_locations):
        dbconnmanager.connect_to_db('database', 'user', 'password',
                                    'localhost', 256, 'utf8')

    assert locationtableview.location_table_model.locations == locations
    assert locationtableview.model().rowCount() == len(locations)


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw', '-s'])
