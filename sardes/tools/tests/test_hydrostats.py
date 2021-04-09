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
import numpy as np
import pytest
import pandas as pd
from qtpy.QtWidgets import QToolBar

# ---- Local imports
from sardes.api.timeseries import DataType
from sardes.tools.hydrostats import (
    SatisticalHydrographTool, compute_monthly_percentiles, MONTHS)


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dataset():
    values = [1, 2, 3, 4, 5, 6, 8, 10, 12, 15]
    data = []
    for year in range(2010, 2016):
        for month in range(1, 13):
            if month == 5:
                continue
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

    return dataset


@pytest.fixture
def hydrostats_tool(dataset, repere_data, obswells_data):

    class ParentToolbar(QToolBar):
        formatted_dataset = dataset

        def model(self):
            sampling_feature_uuid = obswells_data.index[0]

            model = Mock()
            model._obs_well_data = obswells_data.loc[sampling_feature_uuid]
            return model

        def get_formatted_data(self):
            return self.formatted_dataset

    toolbar = ParentToolbar()
    tool = SatisticalHydrographTool(toolbar)

    toolbar.addAction(tool)
    toolbar.show()
    yield tool

    # toolbar.close()
    # assert not tool.toolwidget().isVisible()


# =============================================================================
# ---- Tests
# =============================================================================
@pytest.mark.parametrize('pool', ['all', 'min_max_median', 'median', 'mean'])
def test_compute_monthly_percentiles(dataset, pool):
    """
    Test that computing montly percentiles is working as expected for the
    different modes that are availables.
    """
    dataset = dataset.set_index('datetime', drop=True)

    expected_nyear = [6, 6, 6, 6, 0, 6, 6, 6, 6, 6, 6, 5]
    q = [100, 90, 75, 50, 25, 10, 0]
    expected_percentiles = {
        'all': [15.0, 12.3, 10.0, 5.5, 3.0, 1.9, 1.0],
        'min_max_median': [15.0, 15.0, 15.0, 5.5, 1.0, 1.0, 1.0],
        'median': [5.5, 5.5, 5.5, 5.5, 5.5, 5.5, 5.5],
        'mean': [6.6, 6.6, 6.6, 6.6, 6.6, 6.6, 6.6]
        }[pool]

    percentiles, nyear = compute_monthly_percentiles(
        dataset, q, pool=pool)
    assert nyear.tolist() == expected_nyear
    assert percentiles.columns.tolist() == q
    for month in range(1, 13):
        if month == 5:
            assert np.isnan(percentiles.loc[month].values).all()
        else:
            assert (percentiles.loc[month].values.tolist() ==
                    expected_percentiles)


@pytest.mark.parametrize('pool', ['all', 'min_max_median', 'median', 'mean'])
def test_compute_monthly_percentiles_if_empty(pool):
    """Test that the function does not bug if we pass an empty dataframe."""
    dataset = pd.DataFrame(
        [],
        columns=['datetime', DataType.WaterLevel])
    dataset['datetime'] = pd.to_datetime(dataset['datetime'])
    dataset = dataset.set_index('datetime', drop=True)

    expected_nyear = [0] * 12
    q = [100, 90, 75, 50, 25, 10, 0]
    expected_percentiles = [np.nan] * 7

    percentiles, nyear = compute_monthly_percentiles(
        dataset, q, pool=pool)
    assert nyear.tolist() == expected_nyear
    assert percentiles.columns.tolist() == q
    for month in range(1, 13):
        assert (np.nan_to_num(percentiles.loc[month].values).tolist() ==
                np.nan_to_num(expected_percentiles).tolist())


def test_plot_statistical_hydrograph_if_empy(qtbot, hydrostats_tool):
    """
    Test that no bug occur when trying to plot the statistical.
    hydrograph of an empty dataset.
    """
    assert hydrostats_tool.toolwidget() is None

    # Set an empty formatter dataset in the parent of the hydrostats_tool.
    dataset = pd.DataFrame(
        [],
        columns=['datetime', DataType.WaterLevel])
    dataset['datetime'] = pd.to_datetime(dataset['datetime'])
    hydrostats_tool.parent.formatted_dataset = dataset

    # Show the statistical hydrograph toolwidget.
    hydrostats_tool.trigger()
    qtbot.waitForWindowShown(hydrostats_tool._toolwidget)
    assert hydrostats_tool.toolwidget().isVisible()

    # Assert the state of gui and properties.
    toolwidget = hydrostats_tool.toolwidget()
    assert toolwidget.year() is None
    assert toolwidget.month() is None
    assert toolwidget.move_backward_btn.isEnabled() is False
    assert toolwidget.move_forward_btn.isEnabled() is False


def test_plot_statistical_hydrograph(qtbot, hydrostats_tool):
    """Test that the statistical hydrograph is plotted as expected."""
    assert hydrostats_tool._toolwidget is None

    # Show the statistical hydrograph toolwidget.
    hydrostats_tool.trigger()
    qtbot.waitForWindowShown(hydrostats_tool._toolwidget)
    assert hydrostats_tool._toolwidget.isVisible()

    toolwidget = hydrostats_tool.toolwidget()
    canvas = toolwidget.canvas
    canvas.set_pool('all')

    # Assert years and current year were set as expected.
    year_cbox_texts = [
        toolwidget.year_cbox.itemText(index) for
        index in range(toolwidget.year_cbox.count())]
    assert year_cbox_texts == ['2010', '2011', '2012', '2013', '2014', '2015']

    assert toolwidget.year_cbox.currentText() == '2015'
    assert canvas.year == 2015

    # Assert months and current month were set as expected.
    month_cbox_texts = [
        toolwidget.month_cbox.itemText(index) for
        index in range(toolwidget.month_cbox.count())]
    assert month_cbox_texts == MONTHS.tolist()
    assert toolwidget.month_cbox.currentText() == "Dec"
    assert canvas.month == 12

    # Assert that the figure was plotted as expected.
    assert canvas.figure.axes[0].get_xlabel() == "Year 2015"
    assert canvas.figure.monthlabels[-1].get_text() == "Dec"
    assert canvas.figure.ncountlabels[-1].get_text() == "(5)"

    expected_median = [5.5] * 4 + [np.nan] + [5.5] * 7
    assert canvas.figure.med_wlvl_plot.get_xdata().tolist() == list(range(12))
    assert (np.nan_to_num(canvas.figure.med_wlvl_plot.get_ydata()).tolist() ==
            np.nan_to_num(expected_median).tolist())

    expected_percentiles = {
        (100, 90): (12.3, 15.0),
        (90, 75): (10.0, 12.3),
        (75, 25): (3.0, 10.0),
        (25, 10): (1.9, 3.0),
        (10, 0): (1.0, 1.9)}
    assert len(canvas.figure.percentile_bars) == 5
    for qpair in canvas.figure.percentile_qpairs:
        container = canvas.figure.percentile_bars[qpair]
        assert len(container.patches) == 12
        for i, bar in enumerate(container.patches):
            qbot, qtop = expected_percentiles[qpair]
            assert bar.get_x() == i - bar.get_width() / 2
            if i == 4:
                # We purposely did not add any data for the month of May
                # in our test dataset.
                assert np.isnan(bar.get_y())
                assert np.isnan(bar.get_height())
            else:
                assert bar.get_y() == qbot
                assert bar.get_height() == (qtop - qbot)

    # Change the current year and month and assert that the figure was
    # updated as expected.
    toolwidget.year_cbox.setCurrentIndex(3)
    assert toolwidget.year_cbox.currentText() == '2013'
    assert canvas.year == 2013

    toolwidget.month_cbox.setCurrentIndex(5)
    assert toolwidget.month_cbox.currentText() == "Jun"
    assert canvas.month == 6

    assert canvas.figure.axes[0].get_xlabel() == "Years 2012-2013"
    assert canvas.figure.monthlabels[-1].get_text() == "Jun"
    assert canvas.figure.ncountlabels[-1].get_text() == "(6)"


def test_plot_statistical_hydrograph_if_empy(qtbot, hydrostats_tool):
    """
    Test that no bug occur when trying to plot the statistical.
    hydrograph of an empty dataset.
    """
    assert hydrostats_tool._toolwidget is None

    # Set an empty formatter dataset in the parent of the hydrostats_tool.
    dataset = pd.DataFrame(
        [],
        columns=['datetime', DataType.WaterLevel])
    dataset['datetime'] = pd.to_datetime(dataset['datetime'])
    hydrostats_tool.parent.formatted_dataset = dataset

    # Show the statistical hydrograph toolwidget.
    hydrostats_tool.trigger()
    qtbot.waitForWindowShown(hydrostats_tool._toolwidget)
    assert hydrostats_tool._toolwidget.isVisible()


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
