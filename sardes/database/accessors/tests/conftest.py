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
import os
import os.path as osp
import uuid
from unittest.mock import Mock
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import matplotlib.pyplot as plt
import pandas as pd
import pytest
from qtpy.QtCore import Qt, QPoint
from qtpy.QtWidgets import QMainWindow, QFileDialog


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
def constructlog(tmp_path):
    filename = osp.join(tmp_path, 'constructlog_testfile.pdf')
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3, 4])
    fig.savefig(filename)
    return filename
