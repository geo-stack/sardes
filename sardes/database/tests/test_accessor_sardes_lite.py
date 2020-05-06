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
import datetime
import os.path as osp

# ---- Third party imports
import pytest
import pandas as pd

# ---- Local imports
from sardes.database.accessor_sardes_lite import (
    DatabaseAccessorSardesLite, init_database)


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture(scope="module")
def dbaccessor(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("database")
    dbaccessor = DatabaseAccessorSardesLite(
        osp.join(tmp_path, 'sqlite_database_test.db'))
    init_database(dbaccessor)
    return dbaccessor


# =============================================================================
# ---- Tests
# =============================================================================
def test_observation_wells_interface(dbaccessor):
    """
    Test that the interface for adding, editing and deleting observation
    wells from the database is working as expected.

    Regression test for cgq-qgc/sardes#244.
    """
    obs_wells = dbaccessor.get_observation_wells_data()
    assert len(obs_wells) == 0

    # Add a new observation well to the database.
    sampling_feature_uuid = dbaccessor._create_index('observation_wells_data')
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


def test_sondes_data_interface(dbaccessor):
    """
    Test that the interface for adding, editing and deleting sondes
    from the database is working as expected.
    """
    sonde_models = dbaccessor.get_sonde_models_lib()
    assert len(sonde_models) > 0

    sonde_data = dbaccessor.get_sondes_data()
    assert len(sonde_data) == 0

    # Add a new sonde to the database.
    sonde_feature_uuid = dbaccessor._create_index('sondes_data')
    attribute_values = {
        'sonde_serial_no': '1015973',
        'sonde_model_id': sonde_models.index[0],
        'date_reception': datetime.date(2006, 3, 30),
        'date_withdrawal': pd.NaT,
        'in_repair': False,
        'out_of_order': False,
        'lost': False,
        'off_network': False,
        'sonde_notes': 'This is a fake sonde for testing purposes only.'
        }
    dbaccessor.add_sondes_data(sonde_feature_uuid, attribute_values)

    sonde_data = dbaccessor.get_sondes_data()
    assert len(sonde_data) == 1
    for attribute_name, attribute_value in attribute_values.items():
        if attribute_name == 'date_withdrawal':
            assert pd.isnull(sonde_data.at[sonde_feature_uuid, attribute_name])
        else:
            assert (sonde_data.at[sonde_feature_uuid, attribute_name] ==
                    attribute_value), attribute_name

    # Edit the data of the newly added sonde.
    edited_attribute_values = {
        'sonde_serial_no': '1015973',
        'sonde_model_id': sonde_models.index[1],
        'date_reception': datetime.date(2006, 3, 15),
        'date_withdrawal': datetime.date(2010, 6, 12),
        'in_repair': True,
        'out_of_order': True,
        'lost': True,
        'off_network': True,
        'sonde_notes': 'Edited fake sonde note.'
        }
    for attribute_name, attribute_value in edited_attribute_values.items():
        dbaccessor.set_sondes_data(
            sonde_feature_uuid, attribute_name, attribute_value)

    sonde_data = dbaccessor.get_sondes_data()
    assert len(sonde_data) == 1
    for attribute_name, attribute_value in edited_attribute_values.items():
        assert (sonde_data.at[sonde_feature_uuid, attribute_name] ==
                attribute_value), attribute_name


def test_sonde_installations_interface(dbaccessor):
    """
    Test that the interface for adding, editing and deleting sonde installation
    from the database is working as expected.
    """
    obs_wells_data = dbaccessor.get_observation_wells_data()
    sonde_data = dbaccessor.get_sondes_data()

    sonde_install = dbaccessor.get_sonde_installations()
    assert len(sonde_install) == 0

    # Add a new sonde installation to the database.
    sonde_install_uuid = dbaccessor._create_index('sonde_installation')
    attribute_values = {
        'sampling_feature_uuid': obs_wells_data.index[0],
        'sonde_uuid': sonde_data.index[0],
        'start_date': datetime.date(2006, 4, 12),
        'end_date': pd.NaT,
        'install_depth': 10.25
        }
    dbaccessor.add_sonde_installations(sonde_install_uuid, attribute_values)

    sonde_install = dbaccessor.get_sonde_installations()
    assert len(sonde_install) == 1
    for attribute_name, attribute_value in attribute_values.items():
        if attribute_name == 'end_date':
            assert pd.isnull(
                sonde_install.at[sonde_install_uuid, attribute_name])
        else:
            assert (sonde_install.at[sonde_install_uuid, attribute_name] ==
                    attribute_value), attribute_name

    # Edit the data of the newly added sonde installation.
    edited_attribute_values = {
        'start_date': datetime.date(2006, 4, 1),
        'end_date': datetime.date(2016, 4, 1),
        'install_depth': 11.25
        }
    for attribute_name, attribute_value in edited_attribute_values.items():
        dbaccessor.set_sonde_installations(
            sonde_install_uuid, attribute_name, attribute_value)

    sonde_install = dbaccessor.get_sonde_installations()
    assert len(sonde_install) == 1
    for attribute_name, attribute_value in edited_attribute_values.items():
        assert (sonde_install.at[sonde_install_uuid, attribute_name] ==
                attribute_value), attribute_name

if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
