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
import itertools
import os
import os.path as osp
import shutil
import uuid
from uuid import UUID
from time import sleep
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import numpy as np
import pytest
import pandas as pd
from qtpy.QtCore import QTimer, QCoreApplication
from pandas.api.types import (
    is_datetime64_any_dtype, is_object_dtype, is_bool_dtype)
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

# ---- Local imports
from sardes.utils.data_operations import are_values_equal
from sardes.api.taskmanagers import TaskManagerBase, WorkerBase
from sardes.api.timeseries import DataType
from sardes.api.database_accessor import DatabaseAccessorError
from sardes.database.accessors.accessor_sardes_lite.accessor import (
    DatabaseAccessorSardesLite, CURRENT_SCHEMA_VERSION, DATE_FORMAT,
    SamplingFeature, Location, SamplingFeatureMetadata,
    SamplingFeatureDataOverview, SamplingFeatureAttachment)
from sardes.database.accessors.accessor_helpers import (
    init_tseries_edits, init_tseries_dels)


def assert_dataframe_equals(df1, df2, ignore_index=False):
    """
    Assert whether two Pandas dataframe df1 and df2 are equal or not.
    Account for the fact that the equality of two numpy nan values is False.
    """
    if ignore_index is False:
        for index, column in itertools.product(df1.index, df1.columns):
            x1, x2 = df1.at[index, column], df2.at[index, column]
            assert are_values_equal(x1, x2), '{} != {}'.format(x1, x2)
    else:
        df2 = df2[df1.columns].copy()
        for x1, x2 in zip(df1.values.flatten(), df2.values.flatten()):
            assert are_values_equal(x1, x2), '{} != {}'.format(x1, x2)


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture()
def database(tmp_path):
    return osp.join(tmp_path, 'sqlite_database_test.db')


@pytest.fixture()
def dbaccessor(database):
    """
    A Database SQlite accessor connected to an empty database that is
    reinitialized after each test.
    """
    dbaccessor = DatabaseAccessorSardesLite(database)
    dbaccessor.init_database()
    assert not dbaccessor._session.in_transaction()

    dbaccessor.connect()
    assert dbaccessor.is_connected()
    assert not dbaccessor._session.in_transaction()

    yield dbaccessor

    dbaccessor.close_connection()
    assert not dbaccessor.is_connected()


@pytest.fixture()
def dblocker(database):
    class WorkerTest(WorkerBase):
        def __init__(self, database):
            super().__init__()
            self.dbaccessor = DatabaseAccessorSardesLite(database)

        def _lock_database(self):
            self.dbaccessor.begin_transaction()
            sleep(10)
            self.dbaccessor.commit_transaction()

    dblocker = TaskManagerBase()
    dblocker.set_worker(WorkerTest(database))
    dblocker.dbaccessor = dblocker._worker.dbaccessor

    return dblocker


# =============================================================================
# ---- Tests
# =============================================================================
def test_fill_database(dbaccessor, database_filler):
    """
    Test that filling the test database is working as expected.
    """
    database_filler(dbaccessor)


def test_connection(dbaccessor):
    """
    Test that connecting to the BD fails and succeed as expected.
    """
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


def test_construction_logs_interface(dbaccessor, tmp_path):
    """
    Test that adding, getting and deleting construction logs in the database
    is working as expected.
    """
    attachment_type = 1
    assert dbaccessor.get('attachments_info').empty

    # Add a new observation well to the database.
    sampling_feature_uuid = dbaccessor.add(
        name='observation_wells_data',
        values={})

    for fext in ['.png', '.jpg', '.jpeg', '.tif', '.pdf']:
        # Create a dummy construction log file.
        # Note: we cannot use pyplot directly or we encounter
        # issues with pytest.
        # Note2: we need to keep a reference to the canvas or else it fails.
        figure = Figure()
        canvas = FigureCanvasAgg(figure)
        ax = figure.add_axes([0.1, 0.1, 0.8, 0.8], frameon=True)
        ax.plot([1, 2, 3, 4])

        filename = osp.join(tmp_path, 'test_construction_log') + fext
        figure.savefig(filename)

        # Attach the construction log file.
        dbaccessor.set_attachment(
            sampling_feature_uuid, attachment_type, filename)
        assert len(dbaccessor.get('attachments_info')) == 1

        # Retrieve the construction log file from the database.
        data, name = dbaccessor.get_attachment(
            sampling_feature_uuid, attachment_type)
        assert name == osp.basename(filename)
        with open(filename, 'rb') as f:
            assert f.read() == data

    # Remove the construction log file from the database.
    dbaccessor.del_attachment(sampling_feature_uuid, attachment_type)
    assert dbaccessor.get('attachments_info').empty


def test_manual_measurements_interface(dbaccessor, obswells_data,
                                       manual_measurements):
    """
    Test that adding, editing and retrieving manual water level measurements
    is working as expected.

    Regression test for cgq-qgc/sardes#424
    """
    # Add the observation wells.
    _dict = obswells_data.to_dict('index')
    dbaccessor.add(
        name=obswells_data.attrs['name'],
        values=_dict.values(),
        indexes=_dict.keys()
        )

    # Test the empty manual measurement dataframe is formatted as expected.
    # This covers the issue reported at cgq-qgc/sardes#427.
    saved_manual_measurements = dbaccessor.get('manual_measurements')
    assert saved_manual_measurements.empty
    assert is_datetime64_any_dtype(saved_manual_measurements['datetime'])

    # =========================================================================
    # Add
    # =========================================================================
    _dict = manual_measurements.to_dict('index')
    dbaccessor.add(
        name=manual_measurements.attrs['name'],
        values=_dict.values(),
        indexes=_dict.keys())

    saved_manual_measurements = dbaccessor.get('manual_measurements')
    assert is_datetime64_any_dtype(saved_manual_measurements['datetime'])
    assert_dataframe_equals(saved_manual_measurements, manual_measurements)

    # =========================================================================
    # Edit
    # =========================================================================
    gen_num_value_uuid = manual_measurements.index[0]
    old_values = manual_measurements.loc[gen_num_value_uuid].to_dict()
    edited_values = {
        'sampling_feature_uuid': obswells_data.index[1],
        'datetime': datetime.datetime(2008, 1, 13, 11, 4, 23),
        'value': 7.45,
        'notes': 'test_edit_manual_measurements'}
    for attr_name, attr_value in edited_values.items():
        assert attr_value != old_values[attr_name]
    dbaccessor.set('manual_measurements', gen_num_value_uuid, edited_values)

    saved_manual_measurements = dbaccessor.get('manual_measurements')
    assert is_datetime64_any_dtype(saved_manual_measurements['datetime'])
    assert (saved_manual_measurements.loc[gen_num_value_uuid].to_dict() ==
            edited_values)

    # =========================================================================
    # Delete
    # =========================================================================
    dbaccessor.delete('manual_measurements', gen_num_value_uuid)
    saved_manual_measurements = dbaccessor.get('manual_measurements')
    assert (saved_manual_measurements.to_dict() ==
            manual_measurements.iloc[1:].to_dict())


def test_repere_data_interface(dbaccessor, obswells_data, repere_data):
    """
    Test that adding, editing and retrieving repere data is working as
    expected.
    """
    # Add the observation wells.
    _dict = obswells_data.to_dict('index')
    dbaccessor.add(
        name=obswells_data.attrs['name'],
        values=_dict.values(),
        indexes=_dict.keys()
        )

    # Assert that the empty repere data dataframe is formatted as expected.
    repere_data_bd = dbaccessor.get('repere_data')
    assert repere_data_bd.empty
    assert is_datetime64_any_dtype(repere_data_bd['start_date'])
    assert is_datetime64_any_dtype(repere_data_bd['end_date'])

    # =========================================================================
    # Add
    # =========================================================================
    _dict = repere_data.to_dict('index')
    dbaccessor.add(
        name=repere_data.attrs['name'],
        values=_dict.values(),
        indexes=_dict.keys()
        )

    repere_data_bd = dbaccessor.get('repere_data')
    assert is_datetime64_any_dtype(repere_data_bd['start_date'])
    assert is_datetime64_any_dtype(repere_data_bd['end_date'])
    assert_dataframe_equals(repere_data_bd, repere_data, ignore_index=True)

    # =========================================================================
    # Edit
    # =========================================================================
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
    dbaccessor.set('repere_data', repere_uuid, edited_values)

    repere_data_bd = dbaccessor.get('repere_data')
    assert is_datetime64_any_dtype(repere_data_bd['start_date'])
    assert is_datetime64_any_dtype(repere_data_bd['end_date'])
    assert repere_data_bd.loc[repere_uuid].to_dict() == edited_values

    # =========================================================================
    # Delete
    # =========================================================================

    # Delete the first repere data of the database.
    dbaccessor.delete('repere_data', repere_data_bd.index[0])

    repere_data_bd = dbaccessor.get('repere_data')
    assert len(repere_data_bd) == len(repere_data) - 1

    # Delete the remaining repere data.
    dbaccessor.delete('repere_data', repere_data_bd.index)

    repere_data_bd = dbaccessor.get('repere_data')
    assert is_datetime64_any_dtype(repere_data_bd['start_date'])
    assert is_datetime64_any_dtype(repere_data_bd['end_date'])
    assert len(repere_data_bd) == 0


def test_sonde_installations_interface(dbaccessor, obswells_data, sondes_data,
                                       sondes_installation, readings_data):
    """
    Test that adding, editing and retrieving sonde installations is working as
    expected.
    """
    # Add the observation wells and sondes to the database.
    for _df in [obswells_data, sondes_data]:
        _dict = _df.to_dict('index')
        dbaccessor.add(
            name=_df.attrs['name'],
            values=_dict.values(),
            indexes=_dict.keys())

    # Assert that the empty dataframe of the sonde installations data is
    # formatted as expected.
    sonde_installs_bd = dbaccessor.get('sonde_installations')
    assert sonde_installs_bd.empty
    assert is_datetime64_any_dtype(sonde_installs_bd['start_date'])
    assert is_datetime64_any_dtype(sonde_installs_bd['end_date'])

    # =========================================================================
    # Add
    # =========================================================================
    _dict = sondes_installation.to_dict('index')
    dbaccessor.add(
        name=sondes_installation.attrs['name'],
        values=_dict.values(),
        indexes=_dict.keys())

    sonde_installs_bd = dbaccessor.get('sonde_installations')
    assert is_datetime64_any_dtype(sonde_installs_bd['start_date'])
    assert is_datetime64_any_dtype(sonde_installs_bd['end_date'])
    assert_dataframe_equals(sondes_installation, sonde_installs_bd)

    # =========================================================================
    # Edit
    # =========================================================================
    sonde_install_id = dbaccessor.get('sonde_installations').index[0]
    old_values = sonde_installs_bd.loc[sonde_install_id].to_dict()
    edited_values = {
        'start_date': datetime.datetime(2006, 4, 1),
        'end_date': datetime.datetime(2016, 4, 1),
        'install_depth': 11.25}
    for attribute_name, attribute_value in edited_values.items():
        assert attribute_value != old_values[attribute_name]
    dbaccessor.set('sonde_installations', sonde_install_id, edited_values)

    sonde_installs_bd = dbaccessor.get('sonde_installations')
    for column, value in edited_values.items():
        assert sonde_installs_bd.at[sonde_install_id, column] == value

    # Assert that a process item has been added as expected for each
    # sonde installation.
    process_data = dbaccessor._get_process_data()
    assert len(process_data) == len(sonde_installs_bd)
    for process_id in sonde_installs_bd['process_id'].values:
        assert process_id in process_data.index

    # =========================================================================
    # Delete
    # =========================================================================
    sonde_installs_bd = dbaccessor.get('sonde_installations')
    obswells_data = dbaccessor.get('observation_wells_data')
    sondes_data = dbaccessor.get('sondes_data')

    # We add some readings data related to the first sonde installation and
    # assert that it was linked correctly to the specified sonde
    # installation.
    dbaccessor.add_timeseries_data(
        readings_data, obswells_data.index[0], sonde_installs_bd.index[0])
    readings = dbaccessor.get_timeseries_for_obs_well(obswells_data.index[0])
    assert (readings['sonde_id'] == '1016042').all()
    assert (readings['install_depth'] == 11.25).all()

    # Assert that an observation related to the sonde installation at index 0
    # has been added as expected in the database.
    observations = dbaccessor._get_observation_data()
    sonde_installs_bd = dbaccessor.get('sonde_installations')
    assert len(observations) == 1
    assert (observations.iloc[0]['process_id'] ==
            sonde_installs_bd.iloc[0]['process_id'])

    # Delete the first sonde installation of the database.
    dbaccessor.delete('sonde_installations', sonde_installs_bd.index[0])

    sonde_installs_bd = dbaccessor.get('sonde_installations')
    assert len(sonde_installs_bd) == len(sondes_installation) - 1

    # Delete the remaining repere data.
    dbaccessor.delete('sonde_installations', sonde_installs_bd.index)

    sonde_installs_bd = dbaccessor.get('sonde_installations')
    assert len(sonde_installs_bd) == 0

    # Check that the 'process' and 'observation' were updated accordingly.
    process_data = dbaccessor._get_process_data()
    assert len(process_data) == 0

    observations = dbaccessor._get_observation_data()
    assert len(observations) == 1
    assert pd.isnull(observations.iloc[0]['process_id'])

    readings = dbaccessor.get_timeseries_for_obs_well(obswells_data.index[0])
    assert pd.isnull(readings['sonde_id']).all()
    assert pd.isnull(readings['install_depth']).all()


def test_sonde_models_interface(dbaccessor, sondes_data):
    """
    Test that adding, editing and retrieving sonde models is working as
    expected.
    """
    # Add the inventory of data loggers.
    _dict = sondes_data.to_dict('index')
    dbaccessor.add(
        name=sondes_data.attrs['name'],
        values=_dict.values(),
        indexes=_dict.keys()
        )

    len_sonde_models = len(dbaccessor.get('sonde_models_lib'))
    assert len_sonde_models > 0

    # =========================================================================
    # Add
    # =========================================================================

    # Add a new sonde model to the database.
    sonde_model_id = dbaccessor.add(
        'sonde_models_lib',
        {'sonde_brand': 'some_brand', 'sonde_model': 'some_model'})

    # Assert that the sonde model was added as expected to the database.
    sonde_models_lib = dbaccessor.get('sonde_models_lib')
    assert sonde_model_id == len_sonde_models + 1
    assert len(sonde_models_lib) == len_sonde_models + 1
    assert sonde_models_lib.at[sonde_model_id, 'sonde_brand'] == 'some_brand'
    assert sonde_models_lib.at[sonde_model_id, 'sonde_model'] == 'some_model'
    assert (sonde_models_lib.at[sonde_model_id, 'sonde_brand_model'] ==
            'some_brand some_model')

    # Create a new sonde model id and add a new sonde model to the database,
    # but without an empty model.
    sonde_model_id = dbaccessor.add(
        'sonde_models_lib',
        {'sonde_brand': 'some_brand_2'})

    # Assert that the sonde model was added as expected to the database.
    sonde_models_lib = dbaccessor.get('sonde_models_lib')
    assert sonde_model_id == len_sonde_models + 2
    assert len(sonde_models_lib) == len_sonde_models + 2
    assert sonde_models_lib.at[sonde_model_id, 'sonde_brand'] == 'some_brand_2'
    assert sonde_models_lib.at[sonde_model_id, 'sonde_model'] is None
    assert (sonde_models_lib.at[sonde_model_id, 'sonde_brand_model'] ==
            'some_brand_2')

    # =========================================================================
    # Edit
    # =========================================================================

    # Edit the sonde model of the last item of the sonde models librairie.
    sonde_models = dbaccessor.get('sonde_models_lib')
    sonde_model_id = len(sonde_models)
    dbaccessor.set(
        'sonde_models_lib', sonde_model_id, {'sonde_model': 'some_model_2'})

    # Assert that the attribute of the given sonde model was edited as
    # expected.
    sonde_models = dbaccessor.get('sonde_models_lib')
    assert sonde_models.at[sonde_model_id, 'sonde_model'] == 'some_model_2'
    assert (sonde_models.at[sonde_model_id, 'sonde_brand_model'] ==
            'some_brand_2 some_model_2')

    # =========================================================================
    # Delete
    # =========================================================================

    # Try to delete a sonde model that is used in table 'sonde_installation'.
    sonde_models = dbaccessor.get('sonde_models_lib')
    assert len(sonde_models) == len_sonde_models + 2

    with pytest.raises(DatabaseAccessorError):
        dbaccessor.delete(
            'sonde_models_lib',
            sondes_data.iloc[0]['sonde_model_id'])

    sonde_models = dbaccessor.get('sonde_models_lib')
    assert len(sonde_models) == len_sonde_models + 2

    # Try to delete the last two new sonde models that were added previously
    # in this test and are not referenced in table 'sonde_installation'.
    dbaccessor.delete('sonde_models_lib', sonde_models.index[-1])
    dbaccessor.delete('sonde_models_lib', sonde_models.index[-2])

    sonde_models = dbaccessor.get('sonde_models_lib')
    assert len(sonde_models) == len_sonde_models


def test_sonde_feature_interface(dbaccessor, sondes_data, sondes_installation,
                                 obswells_data):
    """
    Test that adding, editing and retrieving sonde features is working as
    expected.
    """
    # Assert that the empty repere data dataframe is formatted as expected.
    sondes_data_bd = dbaccessor.get('sondes_data')
    assert sondes_data_bd.empty
    assert is_datetime64_any_dtype(sondes_data_bd['date_reception'])
    assert is_datetime64_any_dtype(sondes_data_bd['date_withdrawal'])
    for column in ['in_repair', 'out_of_order', 'lost', 'off_network']:
        assert is_bool_dtype(sondes_data_bd[column])

    # =========================================================================
    # Add
    # =========================================================================
    _dict = sondes_data.to_dict('index')
    dbaccessor.add(
        name=sondes_data.attrs['name'],
        values=_dict.values(),
        indexes=_dict.keys()
        )
    sondes_data_bd = dbaccessor.get('sondes_data')
    assert_dataframe_equals(sondes_data, sondes_data_bd, ignore_index=True)

    # =========================================================================
    # Edit
    # =========================================================================
    sonde_models = dbaccessor.get('sonde_models_lib')
    sonde_id = sondes_data_bd.index[0]
    old_values = sondes_data_bd.loc[sonde_id].to_dict()
    edited_values = {
        'sonde_serial_no': '1015973b',
        'sonde_model_id': sonde_models.index[1],
        'date_reception': datetime.datetime(2006, 3, 15),
        'date_withdrawal': datetime.datetime(2010, 6, 12),
        'in_repair': True,
        'out_of_order': True,
        'lost': True,
        'off_network': True,
        'sonde_notes': 'Edited fake sonde note.'
        }
    for attribute_name, attribute_value in edited_values.items():
        assert attribute_value != old_values[attribute_name]
    dbaccessor.set('sondes_data', sonde_id, edited_values)

    sondes_data_bd = dbaccessor.get('sondes_data')
    for column, value in edited_values.items():
        assert sondes_data_bd.at[sonde_id, column] == value, column

    # =========================================================================
    # Delete
    # =========================================================================

    # Add the observation wells.
    _dict = obswells_data.to_dict('index')
    dbaccessor.add(
        name='observation_wells_data',
        values=_dict.values(),
        indexes=_dict.keys()
        )

    # Add the sonde installations.
    _dict = sondes_installation.to_dict('index')
    dbaccessor.add(
        name='sonde_installations',
        values=_dict.values(),
        indexes=_dict.keys())

    # Try to delete a sonde that is used in table 'sonde_installation'.
    sondes_data_bd = dbaccessor.get('sondes_data')
    assert len(sondes_data_bd) == 6

    sonde_id = sondes_installation.iloc[0]['sonde_uuid']
    with pytest.raises(DatabaseAccessorError):
        dbaccessor.delete('sondes_data', sonde_id)

    sondes_data_bd = dbaccessor.get('sondes_data')
    assert len(sondes_data_bd) == 6

    # We deleted all sonde installations and try to delete all sonde
    # features from the database.
    dbaccessor.delete('sonde_installations', sondes_installation.index)
    dbaccessor.delete('sondes_data', sondes_data.index)

    sondes_data_bd = dbaccessor.get('sondes_data')
    assert len(sondes_data_bd) == 0


def test_observation_well_interface(dbaccessor, database_filler,
                                    obswells_data):
    """
    Test that adding, editing and retrieving  observation wells in the
    database is working as expected.

    Regression test for cgq-qgc/sardes#244.
    """
    obs_wells_bd = dbaccessor.get('observation_wells_data')
    assert obs_wells_bd.empty

    # =========================================================================
    # Add
    # =========================================================================
    database_filler(dbaccessor)

    obs_wells_bd = dbaccessor.get('observation_wells_data')
    assert_dataframe_equals(obswells_data, obs_wells_bd)

    # =========================================================================
    # Edit
    # =========================================================================
    sampling_feature_uuid = obs_wells_bd.index[0]
    edited_values = {
        'obs_well_id': '123A2456_edited',
        'latitude': 42.424242,
        'longitude': -65.656565,
        'common_name': 'well_123A2456_name_edited',
        'municipality': 'well_123A2456_minicipality_edited',
        'aquifer_type': 'well_123A2456_aquifer_type_edited',
        'confinement': 'well_123A2456_confinement_edited',
        'aquifer_code': 555,
        'in_recharge_zone': 2,
        'is_influenced': 2,
        'is_station_active': False,
        'obs_well_notes': 'well_123A2456_notes_edited'
        }

    dbaccessor.set(
        'observation_wells_data',
        sampling_feature_uuid,
        edited_values)

    obs_wells_bd = dbaccessor.get('observation_wells_data')
    for column, value in edited_values.items():
        assert obs_wells_bd.at[sampling_feature_uuid, column] == value, column

    # =========================================================================
    # Delete
    # =========================================================================
    obs_wells_id = obs_wells_bd.index[0]
    assert len(dbaccessor.get('observation_wells_data')) == 5

    # Try to delete a station with readings, repere, sonde installations,
    # and remark.
    with pytest.raises(DatabaseAccessorError):
        dbaccessor.delete('observation_wells_data', obs_wells_id)
    assert len(dbaccessor.get('observation_wells_data')) == 5

    # We delete the timeseries and try again.
    readings = dbaccessor.get_timeseries_for_obs_well(obs_wells_id)
    data_types = [DataType.WaterLevel, DataType.WaterTemp, DataType.WaterEC]
    tseries_dels = init_tseries_dels()
    for data_type in data_types:
        to_delete = readings[
            [data_type, 'datetime', 'obs_id']].dropna(subset=[data_type])
        to_delete['data_type'] = data_type
        to_delete = to_delete.drop(labels=data_type, axis=1)
        tseries_dels = tseries_dels.append(
            to_delete, ignore_index=True)
    dbaccessor.delete_timeseries_data(tseries_dels)

    with pytest.raises(DatabaseAccessorError):
        dbaccessor.delete('observation_wells_data', obs_wells_id)
    assert len(dbaccessor.get('observation_wells_data')) == 5

    # We delete the manual measurements and try again.
    dbaccessor.delete(
        'manual_measurements',
        dbaccessor.get('manual_measurements').index)

    with pytest.raises(DatabaseAccessorError):
        dbaccessor.delete('observation_wells_data', obs_wells_id)
    assert len(dbaccessor.get('observation_wells_data')) == 5

    # We delete the repere data and try again.
    dbaccessor.delete(
        'repere_data', dbaccessor.get('repere_data').index)

    with pytest.raises(DatabaseAccessorError):
        dbaccessor.delete('observation_wells_data', obs_wells_id)
    assert len(dbaccessor.get('observation_wells_data')) == 5

    # We delete all remarks and try again.
    dbaccessor.delete('remarks', dbaccessor.get('remarks').index)

    with pytest.raises(DatabaseAccessorError):
        dbaccessor.delete('observation_wells_data', obs_wells_id)
    assert len(dbaccessor.get('observation_wells_data')) == 5

    # We delete the sonde installations and try again (now it should work).
    dbaccessor.delete(
        'sonde_installations',
        dbaccessor.get('sonde_installations').index)

    dbaccessor.delete('observation_wells_data', obs_wells_id)
    assert len(dbaccessor.get('observation_wells_data')) == 4

    # Assert that the DB was cleaned as expected.
    assert (
        dbaccessor._session.query(Location.loc_id)
        .filter(SamplingFeature.sampling_feature_uuid == obs_wells_id)
        .filter(SamplingFeature.loc_id == Location.loc_id)
        .count()
        ) == 0
    for table in [SamplingFeature, SamplingFeatureMetadata,
                  SamplingFeatureDataOverview, SamplingFeatureAttachment]:
        assert (
            dbaccessor._session.query(table)
            .filter(table.sampling_feature_uuid == obs_wells_id)
            .count()
            ) == 0


def test_remark_types_interface(dbaccessor, database_filler):
    """
    Test that adding, editing and retrieving remark types is working as
    expected.
    """
    database_filler(dbaccessor)

    # =========================================================================
    # Add
    # =========================================================================

    model_remark_types = dbaccessor.get('remark_types')
    assert len(model_remark_types) == 2

    # Add a new remark type.
    new_remark_type_data = {
        'remark_type_code': 'R3',
        'remark_type_name': 'remark type 3',
        'remark_type_desc': 'desc remark type 3'}
    new_remark_type_id = dbaccessor.add('remark_types', new_remark_type_data)
    assert new_remark_type_id == 3

    # Assert that the remark type was added as expected.
    model_remark_types = dbaccessor.get('remark_types')
    assert len(model_remark_types) == 3
    for field, value in new_remark_type_data.items():
        assert model_remark_types.at[new_remark_type_id, field] == value

    # =========================================================================
    # Edit
    # =========================================================================

    edited_remark_type_data = {
        'remark_type_code': 'R3ed',
        'remark_type_name': 'remark type 3ed',
        'remark_type_desc': 'desc remark type 3ed'}

    # Edit the newly added remark type.
    dbaccessor.set('remark_types', new_remark_type_id, edited_remark_type_data)

    # Assert that edits were saved as expected.
    model_remark_types = dbaccessor.get('remark_types')
    for field, value in edited_remark_type_data.items():
        assert model_remark_types.at[new_remark_type_id, field] == value

    # =========================================================================
    # Delete
    # =========================================================================

    # Try to delete a sonde model that is used in table 'remarks'.
    with pytest.raises(DatabaseAccessorError):
        dbaccessor.delete('remark_types', 1)

    model_remark_types = dbaccessor.get('remark_types')
    assert len(model_remark_types) == 3

    # Try to delete the newly added remark type.
    dbaccessor.delete('remark_types', new_remark_type_id)

    model_remark_types = dbaccessor.get('remark_types')
    assert len(model_remark_types) == 2


def test_remarks_interface(dbaccessor, database_filler, obswells_data):
    """
    Test that adding, editing and retrieving remarks is working as expected.
    """
    database_filler(dbaccessor)

    # =========================================================================
    # Add
    # =========================================================================

    model_remarks = dbaccessor.get('remarks')
    assert len(model_remarks) == 2

    # Add a new remark type.
    new_remark_data = {
        'sampling_feature_uuid': obswells_data.index[1],
        'remark_type_id': 1,
        'period_start': datetime.datetime(2006, 6, 6, 6),
        'period_end': datetime.datetime(2009, 9, 9, 9),
        'remark_text': 'remark text no.3',
        'remark_author': 'remark author no.3',
        'remark_date': datetime.datetime(2022, 2, 2, 2),
        }
    new_remark_id = dbaccessor.add('remarks', new_remark_data)
    assert new_remark_id == 3

    # Assert that the remark type was added as expected.
    model_remarks = dbaccessor.get('remarks')
    assert len(model_remarks) == 3
    for field, value in new_remark_data.items():
        assert model_remarks.at[new_remark_id, field] == value

    # =========================================================================
    # Edit
    # =========================================================================

    edited_remark_data = {
        'sampling_feature_uuid': obswells_data.index[0],
        'remark_type_id': 2,
        'period_start': datetime.datetime(2006, 3, 2, 1),
        'period_end': datetime.datetime(2009, 3, 2, 1),
        'remark_text': 'remark text no.3_ed',
        'remark_author': 'remark author no.3_ed',
        'remark_date': datetime.datetime(2022, 3, 2, 1),
        }

    # Edit the newly added remark type.
    dbaccessor.set('remarks', new_remark_id, edited_remark_data)

    # Assert that edits were saved as expected.
    model_remarks = dbaccessor.get('remarks')
    for field, value in edited_remark_data.items():
        assert model_remarks.at[new_remark_id, field] == value

    # =========================================================================
    # Delete
    # =========================================================================

    # Delete the newly added remark.
    dbaccessor.delete('remarks', new_remark_id)

    model_remarks = dbaccessor.get('remarks')
    assert len(model_remarks) == 2


# =============================================================================
# ---- Tests timeseries
# =============================================================================
def test_timeseries_interface(dbaccessor, obswells_data, sondes_data,
                              sondes_installation):
    """
    Test that adding editing and deleting timeseries data in the database
    is working as expected.
    """
    # Add observation wells, sondes, and sonde installations to the
    # database.
    for _df in [obswells_data, sondes_data, sondes_installation]:
        _dict = _df.to_dict('index')
        dbaccessor.add(
            name=_df.attrs['name'],
            values=_dict.values(),
            indexes=_dict.keys()
            )

    # Assert that the accessor correctly return an empty dataframe when
    # no timeseries data is saved in the database for a given sampling feature
    # and data type.
    obs_well_uuid = dbaccessor.get('observation_wells_data').index[0]
    sonde_install_uuid = dbaccessor.get('sonde_installations').index[0]
    for data_type in DataType:
        tseries_data = dbaccessor.get_timeseries_for_obs_well(
            obs_well_uuid, data_type)
    assert tseries_data.empty

    # =========================================================================
    # Add
    # =========================================================================

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
    assert (wlevel_data['obs_id'] == 1).all()
    assert (wlevel_data['sonde_id'] == '1016042').all()

    wtemp_data = dbaccessor.get_timeseries_for_obs_well(
        obs_well_uuid, DataType.WaterTemp)
    assert len(wtemp_data) == 3
    assert (wtemp_data['obs_id'] == 1).all()
    assert (wtemp_data['sonde_id'] == '1016042').all()

    wcond_data = dbaccessor.get_timeseries_for_obs_well(
        obs_well_uuid, DataType.WaterEC)
    assert wcond_data.empty

    # Assert that the sampling feature data overview was updated and
    # cached correctly in the database.
    data_overview = dbaccessor.get('observation_wells_data_overview')
    assert len(data_overview) == 1
    assert data_overview.index[0] == obs_well_uuid
    assert (data_overview.at[obs_well_uuid, 'first_date'] ==
            datetime.datetime(2018, 9, 27))
    assert (data_overview.at[obs_well_uuid, 'last_date'] ==
            datetime.datetime(2018, 9, 29))
    assert data_overview.at[obs_well_uuid, 'mean_water_level'] == 1.2

    # =========================================================================
    # Edit
    # =========================================================================
    tseries_edits = init_tseries_edits()
    tseries_edits.loc[
        (datetime.datetime(2018, 9, 27, 7), 1, DataType.WaterLevel), 'value'
        ] = 3.25
    tseries_edits.loc[
        (datetime.datetime(2018, 9, 28, 7), 1, DataType.WaterTemp), 'value'
        ] = None
    dbaccessor.save_timeseries_data_edits(tseries_edits)

    obs_well_uuid = dbaccessor.get('observation_wells_data').index[0]
    wlevel_data = dbaccessor.get_timeseries_for_obs_well(
        obs_well_uuid, DataType.WaterLevel)
    assert wlevel_data.iloc[0][DataType.WaterLevel] == 3.25

    wtemp_data = dbaccessor.get_timeseries_for_obs_well(
        obs_well_uuid, DataType.WaterTemp)
    assert pd.isnull(wtemp_data.iloc[1][DataType.WaterTemp])

    # Assert that the sampling feature data overview was updated and
    # cached correctly in the database.
    data_overview = dbaccessor.get('observation_wells_data_overview')
    assert data_overview.at[obs_well_uuid, 'mean_water_level'] == 1.917

    # =========================================================================
    # Delete
    # =========================================================================
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

    obs_well_uuid = dbaccessor.get('observation_wells_data').index[0]
    for data_type in [DataType.WaterLevel, DataType.WaterTemp]:
        tseries_data = dbaccessor.get_timeseries_for_obs_well(
            obs_well_uuid, data_type)
        assert len(tseries_data) == 2

    # Assert that the sampling feature data overview was updated and
    # cached correctly in the database.
    data_overview = dbaccessor.get('observation_wells_data_overview')
    assert data_overview.at[obs_well_uuid, 'mean_water_level'] == 2.225
    assert (data_overview.at[obs_well_uuid, 'last_date'] ==
            datetime.datetime(2018, 9, 28))

    # Delete the remaining timeseries data.
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

    obs_well_uuid = dbaccessor.get('observation_wells_data').index[0]
    for data_type in data_types:
        tseries_data = dbaccessor.get_timeseries_for_obs_well(
            obs_well_uuid, data_type)
        assert len(tseries_data) == 0

    # Assert that the sampling feature data overview is now empty as
    # expected.
    data_overview = dbaccessor.get('observation_wells_data_overview')
    assert len(data_overview) == 0


def test_delete_non_existing_data(dbaccessor):
    """
    Test that trying to delete a timeseries data when no data exist in the
    database for the given datatype, datetime and observation id is handled
    correctly by the accessor.

    Regression test for cgq-qgc/sardes#312.
    """
    # Add timeseries data to the database.
    new_tseries_data = pd.DataFrame(
        [['2018-09-27 07:00:00', 1.1, 3],
         ['2018-09-28 07:00:00', 1.2, 4],
         ['2018-09-29 07:00:00', 1.3, 5]],
        columns=['datetime', DataType.WaterLevel, DataType.WaterTemp])
    new_tseries_data['datetime'] = pd.to_datetime(
        new_tseries_data['datetime'], format=DATE_FORMAT)
    dbaccessor.add_timeseries_data(new_tseries_data, None, None)

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
    # Add timeseries data to the database.
    obswell_id = uuid.uuid4()
    new_tseries_data = pd.DataFrame(
        [['2018-09-27 07:00:00', 1.1, 3],
         ['2018-09-28 07:00:00', 1.2, 4],
         ['2018-09-29 07:00:00', 1.3, 5]],
        columns=['datetime', DataType.WaterLevel, DataType.WaterTemp])
    new_tseries_data['datetime'] = pd.to_datetime(
        new_tseries_data['datetime'], format=DATE_FORMAT)
    dbaccessor.add_timeseries_data(new_tseries_data, obswell_id, None)

    # Try editing a timeseries data that doesn't exist in the database for
    # the given datatype, datetime and observation id.
    tseries_edits = init_tseries_edits()
    tseries_edits.loc[
        (datetime.datetime(2018, 9, 29, 7), 1, DataType.WaterEC), 'value'
        ] = 1234.56
    dbaccessor.save_timeseries_data_edits(tseries_edits)

    # Assert that the data we were trying to edit was added and saved
    # correctly in the database.
    waterec_data = dbaccessor.get_timeseries_for_obs_well(
        obswell_id, DataType.WaterEC)
    assert len(waterec_data) == 1
    assert waterec_data.iloc[0][DataType.WaterEC] == 1234.56


def test_add_delete_large_timeseries_record(dbaccessor):
    """
    Test that large time series record are added and deleted as expected
    to and from the database.

    Regression test for cgq-qgc/sardes#378.
    """
    sampling_feature_uuid = uuid.uuid4()

    # Prepare the timeseries data.
    new_tseries_data = pd.DataFrame(
        [], columns=['datetime', DataType.WaterLevel, DataType.WaterTemp])
    new_tseries_data['datetime'] = pd.date_range(
        start='1/1/1960', end='1/1/2020')
    new_tseries_data[DataType.WaterLevel] = np.random.rand(
        len(new_tseries_data))
    new_tseries_data[DataType.WaterTemp] = np.random.rand(
        len(new_tseries_data))
    assert len(new_tseries_data) == 21916

    # Add timeseries data to the database.
    dbaccessor.add_timeseries_data(
        new_tseries_data, sampling_feature_uuid, None)

    wlevel_data = dbaccessor.get_timeseries_for_obs_well(
        sampling_feature_uuid, DataType.WaterLevel)
    assert len(wlevel_data) == 21916

    wtemp_data = dbaccessor.get_timeseries_for_obs_well(
        sampling_feature_uuid, DataType.WaterTemp)
    assert len(wtemp_data) == 21916

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


def test_concurrent_read_write_access(qtbot, dblocker, dbaccessor,
                                      obswells_data):
    """
    Test that multiple users can access the database at the same time.

    See cgq-qgc/sardes#534.
    """
    assert not dbaccessor._session.in_transaction()
    name = obswells_data.attrs['name']
    data = dbaccessor.get(name)
    assert len(data) == 0
    assert not dbaccessor._session.in_transaction()

    assert not dblocker.dbaccessor._session.in_transaction()
    dblocker.add_task('lock_database', callback=None)
    dblocker.run_tasks()
    qtbot.wait(100)
    assert dblocker.dbaccessor._session.in_transaction()

    # Test a writing method.
    assert not dbaccessor._session.in_transaction()
    _dict = obswells_data.to_dict('index')
    indexes = dbaccessor.add(
        name=name,
        values=_dict.values(),
        indexes=_dict.keys()
        )
    assert not dbaccessor._session.in_transaction()

    # Assert that it took more than one try for the dbaccessor to complete
    # the transaction.
    assert dbaccessor._begin_transaction_try_count == 2

    # Test a reading method.
    assert not dblocker.dbaccessor._session.in_transaction()
    dblocker.add_task('lock_database', callback=None)
    dblocker.run_tasks()
    qtbot.wait(100)
    assert dblocker.dbaccessor._session.in_transaction()

    assert not dbaccessor._session.in_transaction()
    data = dbaccessor.get(name)
    assert len(indexes) == 5
    assert len(data) == 5
    assert not dbaccessor._session.in_transaction()

    # Assert that it took more than one try for the dbaccessor to complete
    # the transaction.
    assert dbaccessor._begin_transaction_try_count == 2


def test_update_database_from_v2(tmp_path):
    """
    Test that updating the database from schema version 2 is
    working as expected.
    """
    src_database = osp.join(osp.dirname(__file__), 'rsesq_prod_v2_sample.db')
    dst_database = osp.join(tmp_path, 'rsesq_prod_v2_sample.db')
    shutil.copy(src_database, dst_database)

    dbaccessor = DatabaseAccessorSardesLite(dst_database)
    assert dbaccessor._engine.execute("PRAGMA user_version").first()[0] == 2

    # Update the database to the latest version.
    assert not dbaccessor._session.in_transaction()
    from_version, to_version, error = dbaccessor.update_database()
    assert not dbaccessor._session.in_transaction()

    assert from_version == 2
    assert to_version == 4
    assert error is None
    assert dbaccessor._engine.execute("PRAGMA user_version").first()[0] == 4

    # Try updating the database again to make sure this doesn't cause any bug.
    assert not dbaccessor._session.in_transaction()
    from_version, to_version, error = dbaccessor.update_database()
    assert not dbaccessor._session.in_transaction()

    assert from_version == 4
    assert to_version == 4
    assert error is None
    assert dbaccessor._engine.execute("PRAGMA user_version").first()[0] == 4

    # (V3) Assert that the water quality reports were removed from the
    # database as expected.
    attachments_info = dbaccessor.get('attachments_info')
    assert len(attachments_info) == 4

    # (V3) Assert that the 'remarks' and 'remark_types' tables were created as
    # expected.
    for data_name in ['remarks', 'remark_types']:
        dataf = dbaccessor.get(data_name)
        assert dataf.empty

    # (V3) Assert that the hydrogeochemical tables were created as
    # expected.
    for data_name in ['hg_param_values', 'hg_surveys', 'hg_params',
                      'hg_sampling_methods', 'pump_types', 'purges',
                      'measurement_units']:
        dataf = dbaccessor.get(data_name)
        assert dataf.empty


def test_update_database_from_v3(tmp_path):
    """
    Test that updating the database from schema version 3 is
    working as expected.
    """
    src_database = osp.join(
        osp.dirname(__file__), 'sqlite_database_v3_sardes0.13.0.db')
    dst_database = osp.join(
        tmp_path, 'sqlite_database_v3_sardes0.13.0.db')
    shutil.copy(src_database, dst_database)

    dbaccessor = DatabaseAccessorSardesLite(dst_database)
    assert dbaccessor._engine.execute("PRAGMA user_version").first()[0] == 3

    # Update the database to the latest version.
    assert not dbaccessor._session.in_transaction()
    from_version, to_version, error = dbaccessor.update_database()
    assert not dbaccessor._session.in_transaction()

    assert from_version == 3
    assert to_version == 4
    assert error is None
    assert dbaccessor._engine.execute("PRAGMA user_version").first()[0] == 4

    # (V4) Assert that 'in_recharge_zone' and 'is_influenced' data were
    # correctly converted from strings to integers.
    station_data = dbaccessor.get('observation_wells_data')
    assert station_data['in_recharge_zone'].dtype == 'Int64'
    assert station_data['is_influenced'].dtype == 'Int64'
    assert list(station_data['in_recharge_zone'].values) == [0, 1, 2, 0, 1]
    assert list(station_data['is_influenced'].values) == [0, 0, 2, 0, 0]

    # (V4) Assert that field 'static_water_level' of table 'purge' was
    # correctly changed to 'water_level_drawdown'.
    purges = dbaccessor.get('purges')
    assert 'water_level_drawdown' in purges.columns

    # (V4) Assert that 'hg_labs' table was created and populated as expected.
    hg_labs = dbaccessor.get('hg_labs')
    assert len(hg_labs) == 2
    assert list(hg_labs.lab_code) == ['Lab#1', 'Lab#2']

    # (V4) Assert that values in column 'lab_name' were converted and copied
    # into column 'lab_id' of table 'hg_param_values' as expected.
    hg_values = dbaccessor.get('hg_param_values')
    assert list(hg_values.lab_id) == [1, 1, 2, pd.NA]


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
