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
from datetime import datetime, date
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
         48.81151, -67.53562, True, None],
        ['03040002', 'PO-01', 'Calixa-Lavallée',
         'ROC', 'Confined', 1, 'No', 'No',
         45.74581, -73.28024, True, None]
        ]
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
def sonde_models():
    return pd.DataFrame(
        [['Solinst', 'Barologger M1.5 Gold'],
         ['Solinst', 'LT M10 Gold'],
         ['Solinst', 'LT M10 Edge'],
         ['Solinst', 'Barologger M1.5'],
         ['Solinst', 'LT M10'],
         ['Solinst', 'LT M20 Gold'],
         ['Solinst', 'L M10'],
         ['Telog 1', 'Druck'],
         ['Telog 2', 'Druck'],
         ['In-Situ', 'Troll']],
        columns=['sonde_brand', 'sonde_model']
        )


@pytest.fixture
def sondes_data():
    data = [
        [5, '1016042', date(2006, 3, 30), pd.NaT,
         False, False, False, False, None],
        [5, '1031928', date(2008, 6, 4), pd.NaT,
         False, False, False, False, None],
        [5, '1021777', date(2007, 3, 26), pd.NaT,
         False, False, False, False, None],
        [1, '1016387', date(2006, 3, 30), pd.NaT,
         False, False, False, False, None],
        [4, '1060487', date(2012, 5, 5), pd.NaT,
         False, False, False, False, None],
        [1, '1048409', date(2010, 2, 8), pd.NaT,
         False, False, False, False, None],
        ]
    return pd.DataFrame(
        data,
        index=[uuid.uuid4() for row in data],
        columns=['sonde_model_id', 'sonde_serial_no',
                 'date_reception', 'date_withdrawal', 'in_repair',
                 'out_of_order', 'lost', 'off_network', 'sonde_notes']
        )


@pytest.fixture
def sondes_installation(obswells_data, sondes_data):
    data = [
        [datetime(2006, 8, 24, 18), pd.NaT, 9.02,
         obswells_data.index[0], sondes_data.index[0]],
        [datetime(2009, 7, 24, 19), pd.NaT, 7.19,
         obswells_data.index[1], sondes_data.index[1]],
        [datetime(2007, 11, 14, 19), pd.NaT, 10.1,
         obswells_data.index[2], sondes_data.index[2]],
        [datetime(2007, 11, 14, 19), pd.NaT, 2.0,
         obswells_data.index[2], sondes_data.index[3]],
        [datetime(2012, 5, 5, 19), pd.NaT, 9.24,
         obswells_data.index[3], sondes_data.index[4]],
        [datetime(2012, 5, 5, 19), pd.NaT, 1.0,
         obswells_data.index[3], sondes_data.index[5]]
        ]
    return pd.DataFrame(
        data,
        index=[uuid.uuid4() for row in data],
        columns=['start_date', 'end_date', 'install_depth',
                 'sampling_feature_uuid', 'sonde_uuid']
        )


@pytest.fixture
def readings_data():
    readings_data = pd.DataFrame(
        [], columns=['datetime', DataType.WaterLevel, DataType.WaterTemp])
    readings_data['datetime'] = pd.date_range(
        start='1/1/2015', end='31/12/2020')
    readings_data[DataType.WaterLevel] = np.random.rand(len(readings_data)) + 1
    readings_data[DataType.WaterTemp] = np.random.rand(len(readings_data)) * 10
    readings_data[DataType.WaterEC] = np.random.rand(len(readings_data)) + 100
    return readings_data


@pytest.fixture
def constructlog(tmp_path):
    filename = osp.join(tmp_path, 'constructlog_testfile.pdf')
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3, 4])
    fig.savefig(filename)
    plt.close(fig)
    return filename


@pytest.fixture
def database_filler(
        obswells_data, constructlog, readings_data,
        repere_data, manual_measurements, sondes_data,
        sondes_installation):

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

        # Add sonde data.
        for index, row in sondes_data.iterrows():
            dbaccessor.add_sondes_data(index, row.to_dict())

        # Add sonde installation.
        for index, row in sondes_installation.iterrows():
            dbaccessor.add_sonde_installations(index, row.to_dict())

    return fill_database
