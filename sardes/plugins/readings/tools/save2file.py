# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Standard library imports

import os
import os.path as osp
from io import BytesIO

# ---- Third party imports
from appconfigs.base import get_home_dir, get_config_dir
import pandas as pd
from PIL import Image
from xlsxwriter.exceptions import FileCreateError

# ---- Local imports
from sardes import __appname__
from sardes.api.timeseries import DataType
from sardes.config.locale import _
from sardes.config.main import CONF
from sardes.api.tools import SardesTool
from sardes.utils.fileio import SafeFileSaver

def _format_reading_data(dataf):
    """
    Resample readings data on a daily basis and format it so that
    it can be saved in an Excel workbook.
    """
    data = (
        dataf
        .dropna(subset=[DataType.WaterLevel])
        .groupby('install_depth').resample('D', on='datetime').first()
        .dropna(subset=[DataType.WaterLevel])
        .droplevel(0, axis=0).drop('datetime', axis=1)
        .reset_index(drop=False)
        .sort_values(by=['datetime', 'install_depth'],
                     ascending=[True, True])
        .drop_duplicates(subset='datetime', keep='first')
        )
    data['datetime'] = data['datetime'].dt.date
    data = data[['datetime', DataType.WaterLevel, DataType.WaterTemp]]
    return data

