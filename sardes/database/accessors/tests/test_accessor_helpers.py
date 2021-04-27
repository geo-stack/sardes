# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the accessor helper functions.
"""

# ---- Third party imports
from pandas.api.types import (
    is_datetime64_ns_dtype, is_int64_dtype, is_float_dtype, is_object_dtype)
import pytest

# ---- Local imports
from sardes.api.timeseries import DataType
from sardes.database.accessors.accessor_helpers import create_empty_readings


# =============================================================================
# ---- Tests
# =============================================================================
def test_create_empty_readings():
    """
    Test that connecting to the BD fails and succeed as expected.
    """
    data_types = [DataType.WaterLevel, DataType.WaterTemp]
    empty_readings = create_empty_readings(data_types)

    # Assert the columns are as expected.
    expected_columns = [
        'datetime', 'sonde_id', DataType.WaterLevel, DataType.WaterTemp,
        'install_depth', 'obs_id']
    assert empty_readings.columns.tolist() == expected_columns

    # Assert the dtypes are as expected.
    assert is_datetime64_ns_dtype(empty_readings['datetime'])
    assert is_object_dtype(empty_readings['sonde_id'])
    assert is_float_dtype(empty_readings[DataType.WaterLevel])
    assert is_float_dtype(empty_readings[DataType.WaterTemp])
    assert is_float_dtype(empty_readings['install_depth'])
    assert is_int64_dtype(empty_readings['obs_id'])


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
