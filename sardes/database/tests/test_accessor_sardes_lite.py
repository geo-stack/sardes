# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the DatabaseAccessorSardesLite.
"""

# ---- Standard imports
import os.path as osp
import uuid

# ---- Third party imports
import pytest
import pandas as pd

# ---- Local imports
from sardes.database.accessor_sardes_lite import (
    DatabaseAccessorSardesLite, init_database)


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dbaccessor(tmp_path):
    dbaccessor = DatabaseAccessorSardesLite(
        osp.join(tmp_path, 'sqlite_database_test.db'))
    init_database(dbaccessor)
    return dbaccessor


# =============================================================================
# ---- Tests
# =============================================================================
def test_observation_well_interface(dbaccessor):
    """
    Test that the interface for adding, editing and deleting observation
    wells from the database is working as expected.

    Regression test for cgq-qgc/sardes#244.
    """
    obs_wells = dbaccessor.get_observation_wells_data()
    assert len(obs_wells) == 0

    # Add a new observation well to the database.
    sampling_feature_uuid = uuid.uuid4()
    attribute_values = {
        'obs_well_id': '123A2456',
        'latitude': 48.0775,
        'longitude': -65.24964,
        'common_name': 'well_123A2456_name',
        'municipality': 'well_123A2456_minicipality',
        'aquifer_type': 'well_123A2456_aquifer_type',
        'confinement': 'well_123A2456_confinement',
        'aquifer_code': 5,
        'in_recharge_zone': 'Yes',
        'is_influenced': 'No',
        'is_station_active': True,
        'obs_well_notes': 'well_123A2456_notes'
        }
    dbaccessor.add_observation_wells_data(
        sampling_feature_uuid, attribute_values)

    obs_wells = dbaccessor.get_observation_wells_data()
    assert len(obs_wells) == 1
    for attribute_name, attribute_value in attribute_values.items():
        assert (obs_wells.at[sampling_feature_uuid, attribute_name] ==
                attribute_value), attribute_name

    # Edit the data of the newly added observation well.
    edited_attribute_values = {
        'obs_well_id': '123A2456_edited',
        'latitude': 42.424242,
        'longitude': -65.656565,
        'common_name': 'well_123A2456_name_edited',
        'municipality': 'well_123A2456_minicipality_edited',
        'aquifer_type': 'well_123A2456_aquifer_type_edited',
        'confinement': 'well_123A2456_confinement_edited',
        'aquifer_code': 555,
        'in_recharge_zone': 'Yes_edited',
        'is_influenced': 'No_edited',
        'is_station_active': False,
        'obs_well_notes': 'well_123A2456_notes_edited'
        }
    for attribute_name, attribute_value in edited_attribute_values.items():
        dbaccessor.set_observation_wells_data(
            sampling_feature_uuid, attribute_name, attribute_value)

    obs_wells = dbaccessor.get_observation_wells_data()
    assert len(obs_wells) == 1
    for attribute_name, attribute_value in edited_attribute_values.items():
        assert (obs_wells.at[sampling_feature_uuid, attribute_name] ==
                attribute_value), attribute_name


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
