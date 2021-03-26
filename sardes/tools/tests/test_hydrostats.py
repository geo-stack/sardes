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
from datetime import datetime
import os
import os.path as osp
from unittest.mock import Mock
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
from numpy import nan
import pytest
import pandas as pd
from qtpy.QtWidgets import QToolBar

# ---- Local imports
from sardes import __rootdir__
from sardes.api.timeseries import DataType
from sardes.tools.hydrostats import (
    SatisticalHydrographTool, compute_monthly_percentiles)
from sardes.utils.tests.test_data_operations import format_reading_data
from sardes.database.accessors import DatabaseAccessorSardesLite


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture(scope='module')
def dbaccessor(tmp_path_factory, database_filler):
    tmp_path = tmp_path_factory.mktemp("database")
    dbaccessor = DatabaseAccessorSardesLite(
        osp.join(tmp_path, 'sqlite_database_test.db'))
    dbaccessor.init_database()
    database_filler(dbaccessor)

    return dbaccessor


@pytest.fixture(scope='module')
def dataset():
    values = [1, 2, 3, 4, 5, 6, 8, 10, 12, 15]
    data = []
    for year in range(2010, 2016):
        for month in range(1, 13):
            if year == 2015 and month == 12:
                # We do not add data for the last month of the last year
                # to test that it is working as expected when months
                # do not have the same number of data.
                break
            for i, value in enumerate(values):
                day = i + 1
                data.append([datetime(year, month, day), value])
    dataset = pd.DataFrame(
        data,
        columns=['datetime', DataType.WaterLevel])
    dataset['datetime'] = pd.to_datetime(dataset['datetime'])
    dataset = dataset.set_index('datetime', drop=True)

    return dataset


# =============================================================================
# ---- Tests
# =============================================================================
@pytest.mark.parametrize('pool', ['all', 'min_max_median', 'median', 'mean'])
def test_compute_monthly_percentiles(dataset, pool):
    """
    Test that computing montly percentiles is working as expected for the
    different modes that are availables.
    """
    expected_nyear = [6] * 11 + [5]
    q = [100, 75, 50, 25, 0]
    expected_percentiles = {
        'all': [15.0, 10.0, 5.5, 3.0, 1.0],
        'min_max_median': [15.0, 15.0, 5.5, 1.0, 1.0],
        'median': [5.5, 5.5, 5.5, 5.5, 5.5],
        'mean': [6.6, 6.6, 6.6, 6.6, 6.6]
        }[pool]

    percentiles, nyear = compute_monthly_percentiles(
        dataset, q, pool=pool)
    assert nyear.tolist() == expected_nyear
    assert percentiles.columns.tolist() == q
    for month in range(1, 13):
        assert percentiles.loc[month].values.tolist() == expected_percentiles


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw', '-s'])
