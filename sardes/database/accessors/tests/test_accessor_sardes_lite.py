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

This module depends on a database that is shared among all tests of this
module. Therefore, the tests must be run sequentially and in the right order.
"""

# ---- Standard imports
import datetime
import os
import os.path as osp
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import numpy as np
import pytest
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

# ---- Local imports
from sardes.api.timeseries import DataType
from sardes.api.database_accessor import init_tseries_edits, init_tseries_dels
from sardes.database.accessors.accessor_sardes_lite import (
    DatabaseAccessorSardesLite, CURRENT_SCHEMA_VERSION, DATE_FORMAT)


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture()
def dbaccessor0(tmp_path):
    """
    A Database SQlite accessor connected to an empty database that is
    reinitialized after each test.
    """
    dbaccessor = DatabaseAccessorSardesLite(
        osp.join(tmp_path, 'sqlite_database_test.db'))
    dbaccessor.init_database()

    dbaccessor.connect()
    assert dbaccessor.is_connected()

    return dbaccessor


@pytest.fixture(scope="module")
def dbaccessor(tmp_path_factory):
    """
    A Database SQlite accessor that is connected to a database that is
    shared among all tests that are inter-dependent.
    """
    tmp_path = tmp_path_factory.mktemp("database")
    dbaccessor = DatabaseAccessorSardesLite(
        osp.join(tmp_path, 'sqlite_database_test.db'))
    dbaccessor.init_database()

    dbaccessor.connect()
    assert dbaccessor.is_connected()

    return dbaccessor


# =============================================================================
# ---- Independent Tests
# =============================================================================
def test_connection(dbaccessor0):
    """
    Test that connecting to the BD fails and succeed as expected.
    """
    dbaccessor = dbaccessor0
    dbaccessor.close_connection()

    # Assert that the connection fails if the version of the BD is outdated.
    dbaccessor.execute("PRAGMA user_version = 0")
    dbaccessor.connect()
    assert not dbaccessor.is_connected()
    assert ("The version of this database is 0 and is outdated." in
            str(dbaccessor._connection_error))
    dbaccessor.close_connection()

    # Assert that the connection fails if the version of Sardes is outdated
    # compared to that of the BD.
    dbaccessor.execute(
        "PRAGMA user_version = {}".format(CURRENT_SCHEMA_VERSION + 1))
    dbaccessor.connect()
    assert not dbaccessor.is_connected()
    assert ("Your Sardes application is outdated" in
            str(dbaccessor._connection_error))
    dbaccessor.close_connection()

    # Assert that the connection fails if the application ID of the BD does not
    # match the application ID used for the Sardes SQLite accessor.
    dbaccessor.execute("PRAGMA application_id = 0")
    dbaccessor.connect()
    assert not dbaccessor.is_connected()
    assert ("does not appear to be a Sardes SQLite database" in
            str(dbaccessor._connection_error))
    dbaccessor.close_connection()

    # Assert that the connection fails if the file doesn't exist.
    dbaccessor._database = dbaccessor._database + ".txt"
    dbaccessor.connect()
    assert not dbaccessor.is_connected()
    assert ("does not exist" in str(dbaccessor._connection_error))
    dbaccessor.close_connection()

    # Assert that the connection fails if the file has the wrong extension.
    with open(dbaccessor._database, 'w'):
        pass
    dbaccessor.connect()
    assert not dbaccessor.is_connected()
    assert ("is not a valid database file" in
            str(dbaccessor._connection_error))
    dbaccessor.close_connection()


def test_add_delete_large_timeseries_record(dbaccessor0):
    """
    Test that large time series record are added and deleted as expected
    to and from the database.

    Regression test for cgq-qgc/sardes#378.
    """
    dbaccessor = dbaccessor0
    sampling_feature_uuid = dbaccessor._create_index('observation_wells_data')

    # Prepare the timeseries data.
    new_tseries_data = pd.DataFrame(
        [], columns=['datetime', DataType.WaterLevel, DataType.WaterTemp])
    new_tseries_data['datetime'] = pd.date_range(
        start='1/1/2000', end='1/1/2020')
    new_tseries_data[DataType.WaterLevel] = np.random.rand(
        len(new_tseries_data))
    new_tseries_data[DataType.WaterTemp] = np.random.rand(
        len(new_tseries_data))

    # Add timeseries data to the database.
    dbaccessor.add_timeseries_data(
        new_tseries_data, sampling_feature_uuid, install_uuid=None)

    wlevel_data = dbaccessor.get_timeseries_for_obs_well(
        sampling_feature_uuid, DataType.WaterLevel)
    assert len(wlevel_data) == 7306

    wtemp_data = dbaccessor.get_timeseries_for_obs_well(
        sampling_feature_uuid, DataType.WaterTemp)
    assert len(wtemp_data) == 7306

    # Delete all timeseries data from the database.
    wlevel_data['data_type'] = DataType.WaterLevel
    wtemp_data['data_type'] = DataType.WaterTemp
    tseries_dels = pd.concat((
        wlevel_data[['datetime', 'obs_id', 'data_type']],
        wtemp_data[['datetime', 'obs_id', 'data_type']]
        ))
    dbaccessor.delete_timeseries_data(tseries_dels)

    wlevel_data = dbaccessor.get_timeseries_for_obs_well(
        sampling_feature_uuid, DataType.WaterLevel)
    assert len(wlevel_data) == 0

    wtemp_data = dbaccessor.get_timeseries_for_obs_well(
        sampling_feature_uuid, DataType.WaterTemp)
    assert len(wtemp_data) == 0


def test_add_get_del_construction_logs(dbaccessor0, tmp_path):
    """
    Test that adding, getting and deleting construction logs in the database
    is working as expected.
    """
    attachment_type = 1
    assert dbaccessor0.get_stored_attachments_info().empty

    # Add a new observation well to the database.
    sampling_feature_uuid = dbaccessor0._create_index('observation_wells_data')
    dbaccessor0.add_observation_wells_data(
        sampling_feature_uuid, attribute_values={})

    for fext in ['.png', '.jpg', '.jpeg', '.tif', '.pdf']:
        # Create a dummy construction log file.
        # Note: we cannot use pyplot directly or we encounter
        # issues with pytest.
        figure = Figure()
        canvas = FigureCanvasAgg(figure)
        ax = figure.add_axes([0.1, 0.1, 0.8, 0.8], frameon=True)
        ax.plot([1, 2, 3, 4])

        filename = osp.join(tmp_path, 'test_construction_log') + fext
        figure.savefig(filename)

        # Attach the construction log file.
        dbaccessor0.set_attachment(
            sampling_feature_uuid, attachment_type, filename)
        assert len(dbaccessor0.get_stored_attachments_info()) == 1

        # Retrieve the construction log file from the database.
        data, name = dbaccessor0.get_attachment(
            sampling_feature_uuid, attachment_type)
        assert name == osp.basename(filename)
        with open(filename, 'rb') as f:
            assert f.read() == data

    # Remove the construction log file from the database.
    dbaccessor0.del_attachment(sampling_feature_uuid, attachment_type)
    assert dbaccessor0.get_stored_attachments_info().empty


def test_manual_measurements(dbaccessor0, obswells_data, manual_measurements):
    """
    Test that adding, editing and retrieving manual water level measurements
    is working as expected.

    Regression test for cgq-qgc/sardes#424
    """
    # Add the observation wells.
    for obs_well_uuid, obs_well_data in obswells_data.iterrows():
        dbaccessor0.add_observation_wells_data(
            obs_well_uuid, attribute_values=obs_well_data.to_dict())

    # Test the empty manual measurement dataframe is formatted as expected.
    # This covers the issue reported at cgq-qgc/sardes#427.
    saved_manual_measurements = dbaccessor0.get_manual_measurements()
    assert saved_manual_measurements.empty
    assert is_datetime64_any_dtype(saved_manual_measurements['datetime'])

    # Add manual measurements.
    for index, row in manual_measurements.iterrows():
        dbaccessor0.add_manual_measurements(index, row.to_dict())

    saved_manual_measurements = dbaccessor0.get_manual_measurements()
    assert is_datetime64_any_dtype(saved_manual_measurements['datetime'])
    assert saved_manual_measurements.to_dict() == manual_measurements.to_dict()

    # Edit a manual measurement.
    gen_num_value_uuid = manual_measurements.index[0]
    old_values = manual_measurements.loc[gen_num_value_uuid].to_dict()
    edited_values = {
        'sampling_feature_uuid': obswells_data.index[1],
        'datetime': datetime.datetime(2008, 1, 13, 11, 4, 23),
        'value': 7.45,
        'notes': 'test_edit_manual_measurements'}
    for attribute_name, attribute_value in edited_values.items():
        assert attribute_value != old_values[attribute_name]
        dbaccessor0.set_manual_measurements(
            gen_num_value_uuid, attribute_name, attribute_value)

    saved_manual_measurements = dbaccessor0.get_manual_measurements()
    assert is_datetime64_any_dtype(saved_manual_measurements['datetime'])
    assert (saved_manual_measurements.loc[gen_num_value_uuid].to_dict() ==
            edited_values)

    # Delete a manual measurements.
    dbaccessor0.delete_manual_measurements(gen_num_value_uuid)
    saved_manual_measurements = dbaccessor0.get_manual_measurements()
    assert (saved_manual_measurements.to_dict() ==
            manual_measurements.iloc[1:].to_dict())


def test_repere_data(dbaccessor0, obswells_data, repere_data):
    """
    Test that adding, editing and retrieving repere data is working as
    expected.
    """
    # Add the observation wells.
    for obs_well_uuid, obs_well_data in obswells_data.iterrows():
        dbaccessor0.add_observation_wells_data(
            obs_well_uuid, attribute_values=obs_well_data.to_dict())

    # Test the empty repere data dataframe is formatted as expected.
    repere_data_bd = dbaccessor0.get_repere_data()
    assert repere_data_bd.empty
    assert is_datetime64_any_dtype(repere_data_bd['start_date'])
    assert is_datetime64_any_dtype(repere_data_bd['end_date'])

    # Add repere data.
    for index, row in repere_data.iterrows():
        dbaccessor0.add_repere_data(index, row.to_dict())

    repere_data_bd = dbaccessor0.get_repere_data()
    assert is_datetime64_any_dtype(repere_data_bd['start_date'])
    assert is_datetime64_any_dtype(repere_data_bd['end_date'])

    repere_data_bd = repere_data_bd.replace({np.nan: None})
    assert repere_data_bd.to_dict() == repere_data.to_dict()

    # Edit repere data.
    repere_uuid = repere_data_bd.index[0]
    old_values = repere_data_bd.loc[repere_uuid].to_dict()
    edited_values = {
        'sampling_feature_uuid': obswells_data.index[1],
        'top_casing_alt': 94.6,
        'casing_length': 1.45,
        'start_date': datetime.datetime(2008, 1, 13, 11, 4, 23),
        'end_date': datetime.datetime(2009, 1, 13, 11, 4, 23),
        'is_alt_geodesic': not old_values['is_alt_geodesic'],
        'repere_note': 'new repere note'
        }
    for attribute_name, attribute_value in edited_values.items():
        assert attribute_value != old_values[attribute_name]
        dbaccessor0.set_repere_data(
            repere_uuid, attribute_name, attribute_value)

    repere_data_bd = dbaccessor0.get_repere_data()
    assert is_datetime64_any_dtype(repere_data_bd['start_date'])
    assert is_datetime64_any_dtype(repere_data_bd['end_date'])
    assert repere_data_bd.loc[repere_uuid].to_dict() == edited_values


# =============================================================================
# ---- Inter-dependent Tests
# =============================================================================
def test_add_observation_well(dbaccessor):
    """
    Test that adding an observation well to the database is working
    as expected.

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


def test_edit_observation_well(dbaccessor):
    """
    Test that editing an observation well in the database is working
    as expected.

    Regression test for cgq-qgc/sardes#244.
    """
    sampling_feature_uuid = dbaccessor.get_observation_wells_data().index[0]
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
    dbaccessor.set_observation_wells_data(
        sampling_feature_uuid, edited_attribute_values)

    obs_wells = dbaccessor.get_observation_wells_data()
    for attribute_name, attribute_value in edited_attribute_values.items():
        assert (obs_wells.at[sampling_feature_uuid, attribute_name] ==
                attribute_value), attribute_name


def test_add_sonde_feature(dbaccessor):
    """
    Test that adding a sonde to the database is working as expected.
    """
    sonde_models = dbaccessor.get_sonde_models_lib()
    sonde_data = dbaccessor.get_sondes_data()
    assert len(sonde_data) == 0

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


def test_edit_sonde_feature(dbaccessor):
    """
    Test that editing a sonde in the database is working as expected.
    """
    sonde_models = dbaccessor.get_sonde_models_lib()
    sonde_feature_uuid = dbaccessor.get_sondes_data().index[0]
    edited_attribute_values = {
        'sonde_serial_no': '1015973b',
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
    for attribute_name, attribute_value in edited_attribute_values.items():
        assert (sonde_data.at[sonde_feature_uuid, attribute_name] ==
                attribute_value), attribute_name


def test_add_sonde_installations(dbaccessor):
    """
    Test that adding a sonde installation to the database is working as
    expected.
    """
    obs_wells_uuid = dbaccessor.get_observation_wells_data().index[0]
    sonde_uuid = dbaccessor.get_sondes_data().index[0]
    sonde_install = dbaccessor.get_sonde_installations()
    assert len(sonde_install) == 0

    # Add a new sonde installation to the database.
    sonde_install_uuid = dbaccessor._create_index('sonde_installation')
    attribute_values = {
        'sampling_feature_uuid': obs_wells_uuid,
        'sonde_uuid': sonde_uuid,
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


def test_edit_sonde_installations(dbaccessor):
    """
    Test that editing a sonde installation in the database is working as
    expected.
    """
    sonde_install_uuid = dbaccessor.get_sonde_installations().index[0]
    edited_attribute_values = {
        'start_date': datetime.date(2006, 4, 1),
        'end_date': datetime.date(2016, 4, 1),
        'install_depth': 11.25
        }
    for attribute_name, attribute_value in edited_attribute_values.items():
        dbaccessor.set_sonde_installations(
            sonde_install_uuid, attribute_name, attribute_value)

    sonde_install = dbaccessor.get_sonde_installations()
    for attribute_name, attribute_value in edited_attribute_values.items():
        assert (sonde_install.at[sonde_install_uuid, attribute_name] ==
                attribute_value), attribute_name


def test_add_sonde_models(dbaccessor):
    """
    Test that adding a new sonde model to the database is working as expected.
    """
    len_sonde_models = len(dbaccessor.get_sonde_models_lib())
    assert len_sonde_models > 0

    # Create a new sonde model id and add a new sonde model to the database.
    sonde_model_id = dbaccessor.create_index('sonde_models_lib')
    dbaccessor.add_sonde_models_lib(
        sonde_model_id,
        {'sonde_brand': 'some_brand', 'sonde_model': 'some_model'})

    # Assert that the sonde model was added as expected to the database.
    sonde_models_lib = dbaccessor.get_sonde_models_lib()
    assert sonde_model_id == len_sonde_models + 1
    assert len(sonde_models_lib) == len_sonde_models + 1
    assert sonde_models_lib.at[sonde_model_id, 'sonde_brand'] == 'some_brand'
    assert sonde_models_lib.at[sonde_model_id, 'sonde_model'] == 'some_model'
    assert (sonde_models_lib.at[sonde_model_id, 'sonde_brand_model'] ==
            'some_brand some_model')

    # Create a new sonde model id and add a new sonde model to the database,
    # but without an empty model.
    sonde_model_id = dbaccessor.create_index('sonde_models_lib')
    dbaccessor.add_sonde_models_lib(
        sonde_model_id, {'sonde_brand': 'some_brand_2'})

    # Assert that the sonde model was added as expected to the database.
    sonde_models_lib = dbaccessor.get_sonde_models_lib()
    assert sonde_model_id == len_sonde_models + 2
    assert len(sonde_models_lib) == len_sonde_models + 2
    assert sonde_models_lib.at[sonde_model_id, 'sonde_brand'] == 'some_brand_2'
    assert sonde_models_lib.at[sonde_model_id, 'sonde_model'] is None
    assert (sonde_models_lib.at[sonde_model_id, 'sonde_brand_model'] ==
            'some_brand_2')


def edit_sonde_models(dbaccessor):
    """
    Test that editing an existing sonde model in the database is working
    as expected.
    """
    # Edit the sonde model of the last item that was added to the sonde
    # models librairie in the previous test.
    sonde_models = dbaccessor.get_sonde_models_lib()
    sonde_model_id = len(sonde_models)
    dbaccessor.set_sonde_models_lib(
        sonde_model_id, {'sonde_model': 'some_model_2'})

    # Assert that the attribute of the given sonde model was edited as
    # expected.
    sonde_models = dbaccessor.get_sonde_models_lib()
    assert sonde_models.at[sonde_model_id, 'sonde_model'] == 'some_model_2'
    assert (sonde_models.at[sonde_model_id, 'sonde_brand_model'] ==
            'some_brand_2 some_model_2')


def test_add_timeseries(dbaccessor):
    """
    Test that adding timeseries data to the database is working as expected.
    """
    # Assert that the accessor correctly return an empty dataframe when
    # no timeseries data is saved in the database for a given sampling feature
    # and data type.
    obs_well_uuid = dbaccessor.get_observation_wells_data().index[0]
    sonde_install_uuid = dbaccessor.get_sonde_installations().index[0]
    for data_type in DataType:
        tseries_data = dbaccessor.get_timeseries_for_obs_well(
            obs_well_uuid, data_type)
    assert tseries_data.empty

    # Add new water level and water temperature times series to the database
    # and assert that those were saved and can be retrieved from the database
    # as expected.
    new_tseries_data = pd.DataFrame(
        [['2018-09-27 07:00:00', 1.1, 3],
         ['2018-09-28 07:00:00', 1.2, 4],
         ['2018-09-29 07:00:00', 1.3, 5]],
        columns=['datetime', DataType.WaterLevel, DataType.WaterTemp])
    new_tseries_data['datetime'] = pd.to_datetime(
        new_tseries_data['datetime'], format=DATE_FORMAT)
    dbaccessor.add_timeseries_data(
        new_tseries_data, obs_well_uuid, sonde_install_uuid)

    wlevel_data = dbaccessor.get_timeseries_for_obs_well(
        obs_well_uuid, DataType.WaterLevel)
    assert len(wlevel_data) == 3
    assert wlevel_data['obs_id'].unique() == [1]
    assert wlevel_data['sonde_id'].unique() == ['1015973b']

    wtemp_data = dbaccessor.get_timeseries_for_obs_well(
        obs_well_uuid, DataType.WaterTemp)
    assert len(wtemp_data) == 3
    assert wtemp_data['obs_id'].unique() == [1]
    assert wtemp_data['sonde_id'].unique() == ['1015973b']

    wcond_data = dbaccessor.get_timeseries_for_obs_well(
        obs_well_uuid, DataType.WaterEC)
    assert wcond_data.empty

    # Assert that the sampling feature data overview was updated and
    # cached correctly in the database.
    data_overview = dbaccessor.get_observation_wells_data_overview()
    assert len(data_overview) == 1
    assert data_overview.index[0] == obs_well_uuid
    assert (data_overview.at[obs_well_uuid, 'first_date'] ==
            datetime.date(2018, 9, 27))
    assert (data_overview.at[obs_well_uuid, 'last_date'] ==
            datetime.date(2018, 9, 29))
    assert data_overview.at[obs_well_uuid, 'mean_water_level'] == 1.2


def test_edit_timeseries(dbaccessor):
    """
    Test that editing timeseries data in the database is working as expected.
    """
    tseries_edits = init_tseries_edits()
    tseries_edits.loc[
        (datetime.datetime(2018, 9, 27, 7), 1, DataType.WaterLevel), 'value'
        ] = 3.25
    tseries_edits.loc[
        (datetime.datetime(2018, 9, 28, 7), 1, DataType.WaterTemp), 'value'
        ] = None
    dbaccessor.save_timeseries_data_edits(tseries_edits)

    obs_well_uuid = dbaccessor.get_observation_wells_data().index[0]
    wlevel_data = dbaccessor.get_timeseries_for_obs_well(
        obs_well_uuid, DataType.WaterLevel)
    assert wlevel_data.iloc[0][DataType.WaterLevel] == 3.25

    wtemp_data = dbaccessor.get_timeseries_for_obs_well(
        obs_well_uuid, DataType.WaterTemp)
    assert pd.isnull(wtemp_data.iloc[1][DataType.WaterTemp])

    # Assert that the sampling feature data overview was updated and
    # cached correctly in the database.
    data_overview = dbaccessor.get_observation_wells_data_overview()
    assert data_overview.at[obs_well_uuid, 'mean_water_level'] == 1.917


def test_delete_non_existing_data(dbaccessor):
    """
    Test that trying to delete a timeseries data when no data exist in the
    database for the given datatype, datetime and observation id is handled
    correctly by the accessor.

    Regression test for cgq-qgc/sardes#312.
    """
    # Try deleting a timeseries data when no timeseries exist for the given
    # datatype and observation id.
    tseries_dels = init_tseries_dels()
    tseries_dels = tseries_dels.append(
        {'obs_id': 1,
         'datetime': datetime.datetime(2018, 9, 29, 7),
         'data_type': DataType.WaterEC},
        ignore_index=True)
    dbaccessor.delete_timeseries_data(tseries_dels)

    # Try deleting a timeseries data that doesn't exist in the database for
    # the given datatype, datetime and observation id.
    tseries_dels = init_tseries_dels()
    tseries_dels = tseries_dels.append(
        {'obs_id': 1,
         'datetime': datetime.datetime(2018, 9, 30, 7),
         'data_type': DataType.WaterTemp},
        ignore_index=True)
    dbaccessor.delete_timeseries_data(tseries_dels)


def test_edit_non_existing_data(dbaccessor):
    """
    Test that trying to edit a timeseries data when no data exist in the
    database for the given datatype, datetime and observation id is handled
    correctly by the accessor.

    Regression test for cgq-qgc/sardes#312.
    """
    # Try editing a timeseries data that doesn't exist in the database for
    # the given datatype, datetime and observation id.
    tseries_edits = init_tseries_edits()
    tseries_edits.loc[
        (datetime.datetime(2018, 9, 29, 7), 1, DataType.WaterEC), 'value'
        ] = 1234.56
    dbaccessor.save_timeseries_data_edits(tseries_edits)

    # Assert that the data we were trying to edit was added and saved
    # correctly in the database.
    obs_well_uuid = dbaccessor.get_observation_wells_data().index[0]
    waterec_data = dbaccessor.get_timeseries_for_obs_well(
        obs_well_uuid, DataType.WaterEC)
    assert len(waterec_data) == 1
    assert waterec_data.iloc[0][DataType.WaterEC] == 1234.56


def test_delete_timeseries(dbaccessor):
    """
    Test that deleting timeseries data from the database is working
    as expected.
    """
    data_types = [DataType.WaterLevel, DataType.WaterTemp, DataType.WaterEC]
    tseries_dels = init_tseries_dels()

    # Delete the third data of the timeseries data.

    for data_type in data_types:
        tseries_dels = tseries_dels.append(
            {'obs_id': 1,
             'datetime': datetime.datetime(2018, 9, 29, 7),
             'data_type': data_type},
            ignore_index=True)
    dbaccessor.delete_timeseries_data(tseries_dels)

    obs_well_uuid = dbaccessor.get_observation_wells_data().index[0]
    for data_type in [DataType.WaterLevel, DataType.WaterTemp]:
        tseries_data = dbaccessor.get_timeseries_for_obs_well(
            obs_well_uuid, data_type)
        assert len(tseries_data) == 2

    # Assert that the sampling feature data overview was updated and
    # cached correctly in the database.
    data_overview = dbaccessor.get_observation_wells_data_overview()
    assert data_overview.at[obs_well_uuid, 'mean_water_level'] == 2.225
    assert (data_overview.at[obs_well_uuid, 'last_date'] ==
            datetime.date(2018, 9, 28))

    # Delete the remaning timeseries data.
    for data_type in data_types:
        tseries_dels = tseries_dels.append(
            {'obs_id': 1,
             'datetime': datetime.datetime(2018, 9, 27, 7),
             'data_type': data_type},
            ignore_index=True)
        tseries_dels = tseries_dels.append(
            {'obs_id': 1,
             'datetime': datetime.datetime(2018, 9, 28, 7),
             'data_type': data_type},
            ignore_index=True)
    dbaccessor.delete_timeseries_data(tseries_dels)

    obs_well_uuid = dbaccessor.get_observation_wells_data().index[0]
    for data_type in data_types:
        tseries_data = dbaccessor.get_timeseries_for_obs_well(
            obs_well_uuid, data_type)
        assert len(tseries_data) == 0

    # Assert that the sampling feature data overview is now empty as
    # expected.
    data_overview = dbaccessor.get_observation_wells_data_overview()
    assert len(data_overview) == 0


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
