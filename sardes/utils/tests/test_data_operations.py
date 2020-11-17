# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the data operations functions.
"""

# ---- Standard imports
import os

# ---- Third party imports
from numpy import nan
import pandas as pd
import pytest

# ---- Local imports
from sardes.api.timeseries import DataType
from sardes.utils.data_operations import intervals_extract, format_reading_data


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def source_data():
    source_data = pd.DataFrame(
        data=[
            ['1970-05-01 01:00:00', '64640', 0.1, nan, nan],
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


# =============================================================================
# ---- Tests
# =============================================================================
def test_format_reading_data(source_data):
    """
    Test that formating daily reading data for publishing is working
    as expected.
    """
    reference_altitude = 105
    expected_data = pd.DataFrame(
        data=[
            ['1970-05-01', '64640', reference_altitude - 0.1, nan, nan],
            ['2005-11-01', '64640', reference_altitude - 1.1, -1.1, 3.16],
            ['2005-11-03', '64640', reference_altitude - 4.1, -4.2, 7.16],
            ['2005-11-04', '64640', reference_altitude - 5.1, -5.1, 3.16]],
        columns=[
            'datetime', 'sonde_id', DataType.WaterLevel, DataType.WaterTemp,
            'install_depth'])
    expected_data['datetime'] = pd.to_datetime(
        expected_data['datetime'], format="%Y-%m-%d")

    formatted_data = format_reading_data(source_data, reference_altitude)
    assert formatted_data.equals(expected_data)


def test_intervals_extract():
    """Test that the function intervals_extract is working as expected."""
    sequence = [2, 3, 4, 5, 7, 8, 9, 11, 15, 16]
    expected_result = [[2, 5], [7, 9], [11, 11], [15, 16]]
    assert list(intervals_extract(sequence)) == expected_result


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw', '-s'])
