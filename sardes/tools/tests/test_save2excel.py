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
from sardes.database.accessors.accessor_helpers import create_empty_readings
from sardes import __rootdir__
from sardes.api.timeseries import DataType
from sardes.tools.save2excel import (
    _save_reading_data_to_xlsx, SaveReadingsToExcelTool, QFileDialog)
from sardes.utils.tests.test_data_operations import format_reading_data


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def source_data():
    source_data = pd.DataFrame(
        data=[
            ['2005-11-01 01:00:00', '64640', 1.1, -1.1,   nan,  3.16, 1],
            ['2005-11-01 13:00:00', '64640', 1.2, -1.2,   nan,  3.16, 1],
            ['2005-11-03 01:00:00', '64640', nan, -2.1,   nan,  3.16, 1],
            ['2005-11-03 13:00:00', '64640', nan,  nan,   nan,  3.16, 1],
            ['2005-11-04 01:00:00', '64640', 5.1, -5.1, 100.9,  3.16, 4],
            ['2005-11-04 13:00:00', '64640', 5.2, -5.2, 100.10, 3.16, 5],

            ['2005-11-03 00:30:00', '20640', 3.1, -3.1, 100.5,  9.25, 2],
            ['2005-11-03 12:30:00', '20640', 3.2, -3.2, 100.6,  9.25, 2],

            ['2005-11-03 01:00:00', '78901', 4.1,  nan, 100.7,  7.16, 3],
            ['2005-11-03 13:00:00', '78901', 4.2, -4.2, 100.8,  7.16, 3]],
        columns=[
            'datetime', 'sonde_id', DataType.WaterLevel,
            DataType.WaterTemp, DataType.WaterEC, 'install_depth', 'obs_id'])
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
         'obs_well_id': '0123456',
         'latitude': 45,
         'longitude': -73.34679})


@pytest.fixture
def save_to_excel_tool(qtbot, source_data, repere_data, obs_well_data):

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
    Test that publishing daily readings data to Excel is working as
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

    assert exported_data.shape == (10, 4)
    assert exported_data.iat[0, 2] == 'municipality_test'
    assert exported_data.iat[1, 2] == '0123456'
    assert exported_data.iat[2, 2] == '45'
    assert exported_data.iat[3, 2] == '-73.34679'
    assert exported_data.iat[4, 2] == '100.00 (Geodesic)'

    assert exported_data.iat[6, 0] == 'Date of reading'
    assert exported_data.iat[6, 1] == 'Water level altitude (m MSL)'
    assert exported_data.iat[6, 2] == 'Water temperature (°C)'
    assert exported_data.iat[6, 3] == 'Water electrical conductivity (µS/cm)'

    assert exported_data.iat[9, 0] == '2005-11-04 00:00:00'
    assert exported_data.iat[9, 1] == '99.9'
    assert exported_data.iat[9, 2] == '-5.1'
    assert exported_data.iat[9, 3] == '100.9'


@pytest.mark.parametrize("value", [None, nan, '', 'test'])
def test_save_readings_to_xlsx_when_bad_coord(
        tmp_path, source_data, repere_data, obs_well_data, value):
    """
    Test that publishing daily readings data to Excel is working as
    expected when the lat/lon coordinates for the monitoring station are
    not valid.
    """
    obs_well_data = {
        'municipality': 'municipality_test',
        'obs_well_id': '0123456',
        'latitude': value,
        'longitude': value}

    filename = osp.join(tmp_path, 'test_save_readings_to_excel.xlsx')
    _save_reading_data_to_xlsx(
        filename, 'test_sheet1', format_reading_data(source_data, repere_data),
        obs_well_data, ground_altitude=100, is_alt_geodesic=True)

    exported_data = pd.read_excel(filename, dtype='str', header=None)
    assert pd.isnull(exported_data.iat[2, 2])
    assert pd.isnull(exported_data.iat[3, 2])


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


def test_readings_to_xlsx_if_empty(tmp_path, save_to_excel_tool, mocker):
    """
    Test that the tool to save daily readings data to Excel is working as
    expected even when there is no data saved for the station.
    """
    # Set an empty dataframe for the data of the tool's parent model.
    save_to_excel_tool.table.model().dataf = (
        create_empty_readings([DataType.WaterLevel]))

    # Create and save the XLSX file.
    selectedfilename = osp.join(tmp_path, 'test_save_empty_readings_to_excel')
    selectedfilter = "Excel Workbook (*.xlsx)"
    mocker.patch.object(QFileDialog, 'getSaveFileName',
                        return_value=(selectedfilename, selectedfilter))

    save_to_excel_tool.trigger()
    assert osp.exists(selectedfilename + '.xlsx')

    # Assert that the content is as expected.
    exported_data = pd.read_excel(
        selectedfilename + '.xlsx', dtype='str', header=None)
    assert exported_data.shape == (7, 3)
    assert exported_data.iat[0, 2] == 'municipality_test'
    assert exported_data.iat[1, 2] == '0123456'
    assert exported_data.iat[2, 2] == '45'
    assert exported_data.iat[3, 2] == '-73.34679'
    assert exported_data.iat[4, 2] == '100.00 (Geodesic)'
    assert exported_data.iat[6, 0] == 'Date of reading'
    assert exported_data.iat[6, 1] == 'Water level altitude (m MSL)'


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
