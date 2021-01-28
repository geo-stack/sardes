# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""Fixtures for the database Accessors."""


# ---- Standard imports
from datetime import datetime
import os.path as osp
from random import randrange
import uuid

# ---- Third party imports
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import pytest

# ---- Local imports
from sardes.api.timeseries import DataType


@pytest.fixture
def obswells_data():
    data = [
        ['03037041', "St-Paul-d'Abbotsford", "Saint-Paul-d'Abbotsford",
         'MT', 'Confined', 3, 'No', 'No',
         45.445178, -72.828773, True, None],
        ['02200001', "Réserve de Duchénier", "Saint-Narcisse-de-Rimouski",
         'ROC', 'Unconfined', 2, 'Yes', 'No',
         48.20282, -68.52795, True, None],
        ['02167001', 'Matane', 'Matane',
         'MT', 'Captive', 3, 'No', 'Yes',
         48.81151, -67.53562, True, None]]
    return pd.DataFrame(
        data=data,
        index=[uuid.uuid4() for row in data],
        columns=['obs_well_id', 'common_name', 'municipality',
                 'aquifer_type', 'confinement', 'aquifer_code',
                 'in_recharge_zone', 'is_influenced', 'latitude',
                 'longitude', 'is_station_active', 'obs_well_notes']
        )


@pytest.fixture
def repere_data(obswells_data):
    data = []
    i = 0
    for obs_well_uuid, obs_well_data in obswells_data.iterrows():
        i += 1
        data.append([
            obs_well_uuid,
            randrange(99999) / 100,
            randrange(20, 200) / 100,
            datetime(randrange(2000, 2006), randrange(12) + 1,
                     randrange(28) + 1, randrange(23) + 1),
            None,
            bool(randrange(2)),
            'Note #{}'.format(i)
            ])
    return pd.DataFrame(
        data,
        index=[uuid.uuid4() for row in data],
        columns=['sampling_feature_uuid', 'top_casing_alt', 'casing_length',
                 'start_date', 'end_date', 'is_alt_geodesic', 'repere_note'])


@pytest.fixture
def manual_measurements(obswells_data):
    data = [
        [obswells_data.index[0], datetime(2010, 8, 10, 16, 10, 34), 5.23, ''],
        [obswells_data.index[0], datetime(2010, 11, 10, 12, 55, 22), 4.36, ''],
        [obswells_data.index[0], datetime(2011, 8, 2, 18, 50, 17), 4.91, ''],
        [obswells_data.index[1], datetime(2009, 8, 2, 18, 34, 38), 28.34, ''],
        [obswells_data.index[2], datetime(2015, 8, 2, 18, 37, 23), 14.87, ''],
        [obswells_data.index[2], datetime(2016, 2, 4, 13, 26, 3), 2.03, '']]
    return pd.DataFrame(
        data,
        index=[uuid.uuid4() for row in data],
        columns=['sampling_feature_uuid', 'datetime', 'value', 'notes']
        )


@pytest.fixture
def readings_data():
    readings_data = pd.DataFrame(
        [], columns=['datetime', DataType.WaterLevel, DataType.WaterTemp])
    readings_data['datetime'] = pd.date_range(
        start='1/1/2015', end='31/12/2020')
    readings_data[DataType.WaterLevel] = np.random.rand(len(readings_data))
    readings_data[DataType.WaterTemp] = np.random.rand(len(readings_data))
    readings_data[DataType.WaterEC] = np.random.rand(len(readings_data))
    return readings_data


@pytest.fixture
def constructlog(tmp_path):
    filename = osp.join(tmp_path, 'constructlog_testfile.pdf')
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3, 4])
    fig.savefig(filename)
    return filename


@pytest.fixture
def database_filler(
        obswells_data, constructlog, readings_data,
        repere_data, manual_measurements):

    def fill_database(dbaccessor):
        for obs_well_uuid, obs_well_data in obswells_data.iterrows():
            dbaccessor.add_observation_wells_data(
                obs_well_uuid, attribute_values=obs_well_data.to_dict())

            # Add a construction log.
            dbaccessor.set_construction_log(obs_well_uuid, constructlog)

            # Add timeseries data.
            dbaccessor.add_timeseries_data(
                readings_data, obs_well_uuid, install_uuid=None)

        # Add repere data to the database.
        for index, row in repere_data.iterrows():
            dbaccessor.add_repere_data(index, row.to_dict())

        # Add manual measurements.
        for index, row in manual_measurements.iterrows():
            dbaccessor.add_manual_measurements(index, row.to_dict())

    return fill_database
