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
from sardes.plugins.readings.tools.save2excel import (
    _save_reading_data_to_xlsx, SaveReadingsToExcelTool, QFileDialog)
from sardes.utils.tests.test_data_operations import format_reading_data


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def source_data():
    source_data = pd.DataFrame(
        data=[
            ['2005-11-01 01:00:00', '64640', 1.1, -1.1, 3.16, 1],
            ['2005-11-01 13:00:00', '64640', 1.2, -1.2, 3.16, 1],
            ['2005-11-03 01:00:00', '64640', nan, -2.1, 3.16, 1],
            ['2005-11-03 13:00:00', '64640', nan, -2.2, 3.16, 1],
            ['2005-11-03 00:30:00', '64640', 3.1, -3.1, 9.25, 2],
            ['2005-11-03 12:30:00', '64640', 3.2, -3.2, 9.25, 2],
            ['2005-11-03 01:00:00', '64640', 4.1, nan, 7.16, 3],
            ['2005-11-03 13:00:00', '64640', 4.2, -4.2, 7.16, 3],
            ['2005-11-04 01:00:00', '64640', 5.1, -5.1, 3.16, 4],
            ['2005-11-04 13:00:00', '64640', 5.2, -5.2, 3.16, 5]],
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
def save_to_excel_tool(qtbot, source_data, repere_data, obs_well_data):

    class ParentToolbar(QToolBar):
        def model(self):
            model = Mock()
            model._obs_well_data = obs_well_data
            model._repere_data = repere_data
            model.dataf = source_data
            return model

        def get_formatted_data(self):
            return format_reading_data(
                self.model().dataf, self.model()._repere_data)

    toolbar = ParentToolbar()
    tool = SaveReadingsToExcelTool(toolbar)

    toolbar.addAction(tool)
    qtbot.addWidget(toolbar)
    toolbar.show()
    return tool


# =============================================================================
# ---- Tests
# =============================================================================
def test_save_reading_data_to_xlsx(tmp_path, source_data, repere_data,
                                   obs_well_data):
    """
    Test that publishing daily readings data to Excell is working as
    expected.
    """
    filename = osp.join(tmp_path, 'test_save_readings_to_excel')
    sheetname = 'test_sheet1'
    formatted_data = format_reading_data(source_data, repere_data)
    last_repere_data = (
        repere_data.sort_values(by=['end_date'], ascending=[True]).iloc[-1])
    ground_altitude = (
        last_repere_data['top_casing_alt'] - last_repere_data['casing_length'])
    is_alt_geodesic = last_repere_data['is_alt_geodesic']
    _save_reading_data_to_xlsx(
        filename, sheetname, formatted_data, obs_well_data,
        ground_altitude, is_alt_geodesic, logo_filename=None)
    assert osp.exists(filename + '.xlsx')

    exported_data = pd.read_excel(
        filename + '.xlsx', dtype='str', header=None)

    assert exported_data.shape == (8, 3)
    assert exported_data.iat[0, 2] == 'municipality_test'
    assert exported_data.iat[1, 2] == '0123456'
    assert exported_data.iat[2, 2] == '100.00 (Geodesic)'

    assert exported_data.iat[4, 0] == 'Date of reading'
    assert exported_data.iat[4, 1] == 'Water level altitude (m MSL)'
    assert exported_data.iat[4, 2] == 'Water temperature (°C)'

    assert exported_data.iat[7, 0] == '2005-11-04 00:00:00'
    assert exported_data.iat[7, 1] == '99.9'
    assert exported_data.iat[7, 2] == '-5.1'


def test_save_readings_to_excel_tool(tmp_path, save_to_excel_tool, mocker):
    """
    Test that the tool to save daily readings data to Excel is working as
    expected.
    """

    # Save a file without a logo.
    selectedfilename = osp.join(tmp_path, 'test_save_readings_to_excel')
    selectedfilter = "Excel Workbook (*.xlsx)"
    mocker.patch.object(QFileDialog, 'getSaveFileName',
                        return_value=(selectedfilename, selectedfilter))

    save_to_excel_tool.trigger()
    assert osp.exists(selectedfilename + '.xlsx')

    # Save a file with a logo.
    selectedfilename = osp.join(tmp_path, 'test_save_readings_to_excel2')
    selectedfilter = "Excel Workbook (*.xlsx)"
    mocker.patch.object(QFileDialog, 'getSaveFileName',
                        return_value=(selectedfilename, selectedfilter))

    company_logo_filename = osp.join(
        __rootdir__, 'ressources', 'icons', 'sardes.png')
    mocker.patch('sardes.config.ospath.get_documents_logo_filename',
                 return_value=company_logo_filename)

    save_to_excel_tool.trigger()
    assert osp.exists(selectedfilename + '.xlsx')


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
