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
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pytest

# ---- Local imports
from sardes import __rootdir__
from sardes.plugins.hydrogeochemistry.hgsurveys import (
    read_hgsurvey_data)


# =============================================================================
# ---- Tests
# =============================================================================
def test_read_hgsurvey_data():
    """
    Test that reading HG survey data from an XLSX workbook is working
    as expected.
    """
    xlsx_filename = osp.join(
        __rootdir__, 'plugins', 'hydrogeochemistry', 'tests',
        'test_releve_hydrogeochimique.xlsx')

    data_surveys = read_hgsurvey_data(xlsx_filename)
    for name in ['relevé x', 'relevé x (2)']:
        data_survey = data_surveys[name]

        assert data_survey['hg_surveys_data'] == {
            'obs_well_id': '02000008',
            'hg_survey_datetime': datetime.datetime(2014, 9, 3, 14, 15),
            'hg_survey_operator': 'Nom Opérateur',
            'survey_note': 'Note en lien avec le relevé hydrogéochimique',
            'hg_survey_depth': 10.1,
            'hg_sampling_method_name': 'Échantillonneur',
            'sample_filtered': 1,
            }

        assert data_survey['hg_param_values_data'] == [
            {'hg_param_name': 'param in-situ 1',
             'hg_param_value': '6.68',
             'meas_units_abb': None},
            {'hg_param_name': 'param in-situ 2',
             'hg_param_value': None,
             'meas_units_abb': '°C'},
            {'hg_param_name': 'param in-situ 3',
             'hg_param_value': '> 0.15',
             'meas_units_abb': 'µmhos/cm'},
            ]
        assert data_survey['purges_data'] == [
            {'purge_sequence_no': 1,
             'purge_seq_start': datetime.datetime(2014, 9, 3, 13, 38),
             'purge_seq_end': datetime.datetime(2014, 9, 3, 13, 50),
             'purge_outflow': 6,
             'pumping_depth': 7,
             'pump_type_name': '12 Volts',
             'water_level_drawdown': 4},
            {'purge_sequence_no': 2,
             'purge_seq_start': datetime.datetime(2014, 9, 3, 13, 50),
             'purge_seq_end': datetime.datetime(2014, 9, 3, 14, 15),
             'purge_outflow': None,
             'pumping_depth': None,
             'pump_type_name': '12 Volts',
             'water_level_drawdown': None}
            ]


def test_read_hgsurvey_data():

if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
