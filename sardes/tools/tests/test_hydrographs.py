# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the HydrographTool.
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
from sardes.database.accessors.accessor_helpers import create_empty_readings
from sardes.tools.hydrographs import (
    HydrographTool, HydrographCanvas, QFileDialog)
from sardes.utils.tests.test_data_operations import format_reading_data


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def source_data():
    source_data = pd.DataFrame(
        data=[
            ['1970-11-01 01:00:00', '64640', 1, nan, nan, 0],
            ['1970-11-02 01:00:00', '64640', 1.2, nan, nan, 0],

            ['2005-11-01 01:00:00', '64640', 1.5, 1, 3.16, 1],
            ['2005-11-02 01:00:00', '64640', 1.6, 2, 3.16, 1],
            ['2005-11-03 01:00:00', '64640', 1.7, 3, 3.16, 1],

            ['2009-11-01 01:00:00', '64640', 0.5, 1, 3.16, 1],
            ['2009-11-02 01:00:00', '64640', 0.6, 2, 3.16, 1],
            ['2009-11-03 01:00:00', '64640', 0.7, 3, 3.16, 1],
            ['2009-11-05 01:00:00', '64640', 0.8, 3, 3.16, 1],
            ['2009-11-06 01:00:00', '64640', 0.9, 3, 3.16, 1]],
        columns=[
            'datetime', 'sonde_id', DataType.WaterLevel,
            DataType.WaterTemp, 'install_depth', 'obs_id'])
    source_data['datetime'] = pd.to_datetime(
        source_data['datetime'], format="%Y-%m-%d %H:%M:%S")
    return source_data


@pytest.fixture
def repere_data():
    return pd.DataFrame(
        [[105, 5, True, datetime(2005, 11, 1, 1), None]],
        columns=['top_casing_alt', 'casing_length', 'is_alt_geodesic',
                 'start_date', 'end_date']
        )


@pytest.fixture
def obs_well_data():
    return pd.Series(
        {'municipality': 'municipality_test',
         'obs_well_id': '0123456'})


@pytest.fixture
def hydrograph_tool(qtbot, source_data, repere_data, obs_well_data):

    class ParentToolbar(QToolBar):
        def __init__(self):
            super().__init__()
            self._model = Mock()
            self._model._obs_well_data = obs_well_data
            self._model._repere_data = repere_data
            self._model.dataf = source_data

        def model(self):
            return self._model

        def get_formatted_data(self):
            return format_reading_data(
                self.model().dataf, self.model()._repere_data)

    toolbar = ParentToolbar()
    tool = HydrographTool(toolbar)

    toolbar.addAction(tool)
    qtbot.addWidget(toolbar)
    toolbar.show()
    return tool


# =============================================================================
# ---- Tests
# =============================================================================
def test_create_hydrograph(tmp_path, source_data, repere_data, obs_well_data,
                           mocker):
    """
    Test that creating an hydrogaph figure is working as expected.
    """
    last_repere_data = (
        repere_data.sort_values(by=['end_date'], ascending=[True]).iloc[-1])
    ground_altitude = (
        last_repere_data['top_casing_alt'] - last_repere_data['casing_length'])
    is_alt_geodesic = last_repere_data['is_alt_geodesic']

    # Test that it is working when no corporate logo is available.
    mocker.patch('sardes.config.ospath.get_documents_logo_filename',
                 return_value=None)
    HydrographCanvas(
        format_reading_data(source_data, repere_data),
        obs_well_data,
        ground_altitude,
        is_alt_geodesic)

    # Test that it is working when a corporate logo is available.
    company_logo_filename = osp.join(
        __rootdir__, 'ressources', 'icons', 'sardes.png')
    mocker.patch('sardes.config.ospath.get_documents_logo_filename',
                 return_value=company_logo_filename)
    HydrographCanvas(
        format_reading_data(source_data, repere_data),
        obs_well_data,
        ground_altitude,
        is_alt_geodesic)


def test_save_hydrograph(tmp_path, hydrograph_tool, mocker):
    """
    Test that creating an saving and hydrogaph figure with the tool is working
    as expected.
    """
    fexts_filters = {
        '.pdf': 'Portable Document Format (*.pdf)',
        '.svg': 'Scalable Vector Graphics (*.svg)',
        '.png': 'Portable Network Graphics (*.png)',
        '.jpg': 'JPEG (*.jpg)'}
    for fext, selectedfilter in fexts_filters.items():
        selectedfilename = osp.join(tmp_path, 'test_save_hydrograph')
        mocker.patch.object(QFileDialog, 'getSaveFileName',
                            return_value=(selectedfilename, selectedfilter))

        hydrograph_tool.trigger()
        assert osp.exists(selectedfilename + fext)


def test_save_hydrograph_if_empty(tmp_path, hydrograph_tool, mocker):
    """
    Test that creating an saving and hydrogaph figure with the tool is working
    as expected when there is no data saved for the station.
    """
    # Set an empty dataframe for the data of the tool's parent model.
    hydrograph_tool.table.model().dataf = (
        create_empty_readings([DataType.WaterLevel, DataType.WaterTemp]))

    # Create and save the hydrograph.
    selectedfilename = osp.join(tmp_path, 'test_save_empty_hydrograph.pdf')
    selectedfilter = 'Portable Document Format (*.pdf)'
    mocker.patch.object(QFileDialog, 'getSaveFileName',
                        return_value=(selectedfilename, selectedfilter))

    hydrograph_tool.trigger()
    assert osp.exists(selectedfilename)


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
