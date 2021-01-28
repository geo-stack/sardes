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
import os
import os.path as osp
from random import randrange
import uuid
from unittest.mock import Mock
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
from numpy import nan
import matplotlib.pyplot as plt
import pandas as pd
import pytest
from qtpy.QtCore import Qt, QPoint
from qtpy.QtWidgets import QMainWindow, QFileDialog

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
        ['02600001', "L'Islet", "L'Islet",
         'ROC', 'Unconfined', 2, 'Yes', 'No',
         47.093526, -70.338989, True, None],
        ['03040002', 'PO-01', 'Calixa-Lavallée',
         'ROC', 'Confined', 1, 'No', 'No',
         45.74581, -73.28024, True, None]]
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
        columns=['sampling_feature_uuid', 'datetime', 'value', 'notes']
        )


@pytest.fixture
def readings_data():
    data = [
        ['1970-11-01 01:00:00', 1,   nan,  nan, 0],
        ['1970-11-02 01:00:00', 3,   nan,  nan, 0],

        ['2005-11-01 01:00:00', 1,   nan, 3.16, 2],
        ['2005-11-02 01:00:00', 2, 100.1, 3.16, 2],
        ['2005-11-03 01:00:00', 3, 100.1, 3.16, 2],

        ['2009-11-01 01:00:00', 1, 100.1, 3.16, 1],
        ['2009-11-02 01:00:00', 2, 100.1, 3.16, 1],
        ['2009-11-03 01:00:00', 3, 100.1, 3.16, 1],
        ['2009-11-05 01:00:00', 3, 100.1, 3.16, 1],
        ['2009-11-06 01:00:00', 3, 100.1, 3.16, 1]]
    source_data = pd.DataFrame(
        data,
        columns=['datetime', DataType.WaterLevel,
                 DataType.WaterTemp, DataType.WaterEC, 'obs_id'])
    source_data['datetime'] = pd.to_datetime(
        source_data['datetime'], format="%Y-%m-%d %H:%M:%S")
    return source_data


@pytest.fixture
def constructlog(tmp_path):
    filename = osp.join(tmp_path, 'constructlog_testfile.pdf')
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3, 4])
    fig.savefig(filename)
    return filename
