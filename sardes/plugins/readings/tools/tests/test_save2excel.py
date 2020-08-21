# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the SaveReadingsToExcelTool.
"""

# ---- Standard imports
import os
import os.path as osp
import sys
from unittest.mock import Mock
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
from numpy import nan
import pytest
import pandas as pd
from qtpy.QtCore import Qt

# ---- Local imports
from sardes.api.timeseries import DataType
from sardes.plugins.readings.tools.save2excel import (
    _format_reading_data, _save_reading_data_to_xlsx)
from sardes.database.database_manager import DatabaseConnectionManager


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def source_data():
    source_data = pd.DataFrame(
        data=[
            ['2005-11-01 01:00:00', '64640', 1.1, -1.1, 3.16],
            ['2005-11-01 13:00:00', '64640', 1.2, -1.2, 3.16],
            ['2005-11-03 01:00:00', '64640', nan, -2.1, 3.16],
            ['2005-11-03 13:00:00', '64640', nan, -2.2, 3.16],
            ['2005-11-03 00:30:00', '64640', 3.1, -3.1, 9.25],
            ['2005-11-03 12:30:00', '64640', 3.2, -3.2, 9.25],
            ['2005-11-03 01:00:00', '64640', 4.1, nan, 7.16],
            ['2005-11-03 13:00:00', '64640', 4.2, -4.2, 7.16],
            ['2005-11-04 01:00:00', '64640', 5.1, -5.1, 3.16],
            ['2005-11-04 13:00:00', '64640', 5.2, -5.2, 3.16]],
        columns=[
            'datetime', 'sonde_id', DataType.WaterLevel,
            DataType.WaterTemp, 'install_depth'])
    source_data['datetime'] = pd.to_datetime(
        source_data['datetime'], format="%Y-%m-%d %H:%M:%S")
    return source_data


@pytest.fixture
def repere_data():
    return pd.Series(
        {'top_casing_alt': 105,
         'casing_length': 5,
         'is_alt_geodesic': True})


# =============================================================================
# ---- Tests
# =============================================================================
def test_format_reading_data(source_data, repere_data):
    """
    Test that formating daily reading data for publishing is working
    as expected.
    """
    expected_data = pd.DataFrame(
        data=[
            ['2005-11-01', 105 - 1.1, -1.1],
            ['2005-11-03', 105 - 4.1, -4.2],
            ['2005-11-04', 105 - 5.1, -5.1]],
        columns=[
            "Date of reading", "Water level altitude (m)",
            "Water temperature (°C)"])
    expected_data["Date of reading"] = pd.to_datetime(
        expected_data["Date of reading"], format="%Y-%m-%d")

    formatted_data = _format_reading_data(source_data, repere_data)
    assert formatted_data.equals(expected_data)


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])

