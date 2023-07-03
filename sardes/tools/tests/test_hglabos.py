# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the HG survey import tool.
"""

# ---- Standard imports
import os
import os.path as osp
import datetime
from uuid import UUID
from unittest.mock import Mock
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pytest
from qtpy.QtWidgets import QToolBar

# ---- Local imports
from sardes import __rootdir__
from sardes.database.accessors.accessor_errors import ImportHGSurveysError
from sardes.tools.hglabos import (
    HGLaboImportTool, read_hglab_data, format_hglab_data)


# =============================================================================
# ---- Tests
# =============================================================================
# Note that only the base functions are tested here. The tool is tested
# in test_table_hg_param_values.py

def test_read_hglab_report():
    """
    Test that reading data from a HG lab report is working as expected.
    """
    xlsx_filename = osp.join(
        __rootdir__, 'tools', 'tests', 'test_read_hglabo.xlsx')

    data_reports = read_hglab_data(xlsx_filename)
    for name in ['rapport x', 'rapport x (2)']:
        data_report = data_reports[name]

        assert len(data_report) == 3

        assert data_report[0] == {
            'lab_report_date': datetime.datetime(2023, 6, 19),
            'lab_code': '0105',
            'obs_well_id': '03037041',
            'hg_survey_datetime': datetime.datetime(2011, 8, 2, 15, 20),
            'lab_sample_id': 'ech001',
            'hg_param_expr': 'param 1',
            'hg_param_value': '0.34',
            'lim_detection': 0.11,
            'meas_units_abb': 'µg/L',
            'method': 'méthode #1',
            'notes': 'note param #1',
            }
        assert data_report[1] == {
            'lab_report_date': datetime.datetime(2023, 6, 19),
            'lab_code': '0105',
            'obs_well_id': '03037041',
            'hg_survey_datetime': datetime.datetime(2011, 8, 2, 15, 20),
            'lab_sample_id': None,
            'hg_param_expr': 'param 2',
            'hg_param_value': '< 0.12',
            'lim_detection': 0.12,
            'meas_units_abb': None,
            'method': 'méthode #1',
            'notes': None,
            }
        assert data_report[2] == {
            'lab_report_date': datetime.datetime(2023, 6, 19),
            'lab_code': '0105',
            'obs_well_id': '02167001',
            'hg_survey_datetime': datetime.datetime(2019, 9, 9),
            'lab_sample_id': 'ech002',
            'hg_param_expr': 'param 3',
            'hg_param_value': None,
            'lim_detection': None,
            'meas_units_abb': '‰',
            'method': None,
            'notes': 'note param #3',
            }

if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
