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
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pytest

# ---- Local imports
from sardes import __rootdir__
from sardes.database.accessors.accessor_errors import ImportHGSurveysError
from sardes.plugins.hydrogeochemistry.hgsurveys import (
    read_hgsurvey_data, format_hg_survey_imported_data,
    format_purge_imported_data, format_params_data_imported_data)


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


def test_format_hgsurvey_imported_data(dbaccessor):
    kwargs = {
        'hg_surveys_data': dbaccessor.get('hg_surveys'),
        'stations_data': dbaccessor.get('observation_wells_data'),
        'hg_sampling_methods_data': dbaccessor.get('hg_sampling_methods')
        }

    data = {
        'obs_well_id': None,
        'hg_survey_datetime': None,
        'hg_survey_operator': None,
        'survey_note': None,
        'hg_survey_depth': None,
        'hg_sampling_method_name': None,
        'sample_filtered': None,
        }

    # Work through all expected error that could be
    # raised in the tested function for the required attributes.

    # The obs_well_id is None.
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_hg_survey_imported_data('survey_test', data, **kwargs)
    assert excinfo.value.code == 101

    # The obs_well_id does not exist.
    data['obs_well_id'] = '12345'
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_hg_survey_imported_data('survey_test', data, **kwargs)
    assert excinfo.value.code == 102

    data['obs_well_id'] = '03037041'

    # The hg_survey_datetime is not valid.
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_hg_survey_imported_data('survey_test', data, **kwargs)
    assert excinfo.value.code == 103

    # Duplicate HG survey.
    data['hg_survey_datetime'] = datetime.datetime(2011, 8, 2, 15, 20)
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_hg_survey_imported_data('survey_test', data, **kwargs)
    assert excinfo.value.code == 104

    # The next call should not raise any error.
    data['hg_survey_datetime'] = datetime.datetime(2013, 5, 25, 10, 15)
    fmt_data = format_hg_survey_imported_data('survey_test', data, **kwargs)

    assert fmt_data == {
        'sampling_feature_uuid': UUID('3c6d0e15-6775-4304-964a-5db89e463c55'),
        'hg_survey_datetime': datetime.datetime(2013, 5, 25, 10, 15),
        'hg_survey_operator': None,
        'survey_note': None,
        'hg_survey_depth': None,
        'hg_sampling_method_id': None,
        'sample_filtered': None,
        }

    # Work through all expected error that could be
    # raised in the tested function for the optional attributes.
    data['hg_survey_depth'] = 'dummy'
    data['hg_sampling_method_name'] = 'dummy'
    data['sample_filtered'] = '4'

    # The hg_survey_depth is not valid.
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_hg_survey_imported_data('survey_test', data, **kwargs)
    assert excinfo.value.code == 105

    data['hg_survey_depth'] = 12.5

    # The hg_sampling_method_name does not exist.
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_hg_survey_imported_data('survey_test', data, **kwargs)
    assert excinfo.value.code == 106

    data['hg_sampling_method_name'] = 'Method #1'

    # The sample_filtered is not valid.
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_hg_survey_imported_data('survey_test', data, **kwargs)
    assert excinfo.value.code == 107

    data['sample_filtered'] = 1

    # The next call should not raise any error.
    data['hg_survey_datetime'] = datetime.datetime(2013, 5, 25, 10, 15)
    fmt_data = format_hg_survey_imported_data('survey_test', data, **kwargs)

    assert fmt_data == {
        'sampling_feature_uuid': UUID('3c6d0e15-6775-4304-964a-5db89e463c55'),
        'hg_survey_datetime': datetime.datetime(2013, 5, 25, 10, 15),
        'hg_survey_operator': None,
        'survey_note': None,
        'hg_survey_depth': 12.5,
        'hg_sampling_method_id': 1,
        'sample_filtered': 1,
        }

    # Test that hg_survey_operator and survey_note are
    # preserved as expected.
    data['hg_survey_operator'] = 'Test survey operator'
    data['survey_note'] = 'Test survey note'
    fmt_data = format_hg_survey_imported_data('survey_test', data, **kwargs)

    assert fmt_data == {
        'sampling_feature_uuid': UUID('3c6d0e15-6775-4304-964a-5db89e463c55'),
        'hg_survey_datetime': datetime.datetime(2013, 5, 25, 10, 15),
        'hg_survey_operator': 'Test survey operator',
        'survey_note': 'Test survey note',
        'hg_survey_depth': 12.5,
        'hg_sampling_method_id': 1,
        'sample_filtered': 1,
        }


def test_format_purge_imported_data(dbaccessor):
    kwargs = {
        'pump_type_data': dbaccessor.get('pump_types'),
        }

    data = [{'purge_sequence_no': None,
             'purge_seq_start': None,
             'purge_seq_end': None,
             'purge_outflow': None,
             'pumping_depth': None,
             'pump_type_name': None,
             'water_level_drawdown': None},
            {'purge_sequence_no': None,
             'purge_seq_start': None,
             'purge_seq_end': None,
             'purge_outflow': None,
             'pumping_depth': None,
             'pump_type_name': None,
             'water_level_drawdown': None
             }]

    # The purge_seq_start is not valid.
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_purge_imported_data('survey_test', data, **kwargs)
    assert excinfo.value.code == 201

    data[0]['purge_seq_start'] = datetime.datetime(2013, 5, 25, 10, 15)

    # The purge_seq_end is not valid.
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_purge_imported_data('survey_test', data, **kwargs)
    assert excinfo.value.code == 203

    # The purge_seq_end < purge_seq_start.
    data[0]['purge_seq_end'] = datetime.datetime(2013, 5, 25, 10, 15)

    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_purge_imported_data('survey_test', data, **kwargs)
    assert excinfo.value.code == 204

    data[0]['purge_seq_end'] = datetime.datetime(2013, 5, 25, 10, 20)

    # The pump type name is not valid.
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_purge_imported_data('survey_test', data, **kwargs)
    assert excinfo.value.code == 205

    data[0]['pump_type_name'] = 'PUMP#1'
    data[1]['pump_type_name'] = 'PUMP#1'

    # The purge outflow is not valid.
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_purge_imported_data('survey_test', data, **kwargs)
    assert excinfo.value.code == 206

    data[0]['purge_outflow'] = 13.5
    data[1]['purge_outflow'] = 15.8

    # The purge_seq_end[0] > purge_seq_start[1].
    data[1]['purge_seq_start'] = datetime.datetime(2013, 5, 25, 10, 18)
    data[1]['purge_seq_end'] = datetime.datetime(2013, 5, 25, 10, 30)

    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_purge_imported_data('survey_test', data, **kwargs)
    assert excinfo.value.code == 202

    data[1]['purge_seq_start'] = datetime.datetime(2013, 5, 25, 10, 20)

    # The next call should not raise any error.
    fmt_data = format_purge_imported_data('survey_test', data, **kwargs)
    assert fmt_data == [
        {'hg_survey_id': 'survey_test',
         'purge_sequence_no': 1,
         'purge_seq_start': datetime.datetime(2013, 5, 25, 10, 15),
         'purge_seq_end': datetime.datetime(2013, 5, 25, 10, 20),
         'purge_outflow': 13.5,
         'pumping_depth': None,
         'pump_type_id': 1,
         'water_level_drawdown': None},
        {'hg_survey_id': 'survey_test',
         'purge_sequence_no': 2,
         'purge_seq_start': datetime.datetime(2013, 5, 25, 10, 20),
         'purge_seq_end': datetime.datetime(2013, 5, 25, 10, 30),
         'purge_outflow': 15.8,
         'pumping_depth': None,
         'pump_type_id': 1,
         'water_level_drawdown': None
         }]

    # The pumping_depth is not valid.
    data[0]['pumping_depth'] = 'dummy'

    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_purge_imported_data('survey_test', data, **kwargs)
    assert excinfo.value.code == 207

    data[0]['pumping_depth'] = 24.65
    data[1]['pumping_depth'] = 12.333

    # The water_level_drawdown is not valid.
    data[0]['water_level_drawdown'] = 'dummy'
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_purge_imported_data('survey_test', data, **kwargs)
    assert excinfo.value.code == 208

    data[0]['water_level_drawdown'] = 3.12
    data[1]['water_level_drawdown'] = 8.45

    # The next call should not raise any error.
    fmt_data = format_purge_imported_data('survey_test', data, **kwargs)
    assert fmt_data == [
        {'hg_survey_id': 'survey_test',
         'purge_sequence_no': 1,
         'purge_seq_start': datetime.datetime(2013, 5, 25, 10, 15),
         'purge_seq_end': datetime.datetime(2013, 5, 25, 10, 20),
         'purge_outflow': 13.5,
         'pumping_depth': 24.65,
         'pump_type_id': 1,
         'water_level_drawdown': 3.12},
        {'hg_survey_id': 'survey_test',
         'purge_sequence_no': 2,
         'purge_seq_start': datetime.datetime(2013, 5, 25, 10, 20),
         'purge_seq_end': datetime.datetime(2013, 5, 25, 10, 30),
         'purge_outflow': 15.8,
         'pumping_depth': 12.333,
         'pump_type_id': 1,
         'water_level_drawdown': 8.45
         }]


def test_format_params_data_imported_data(dbaccessor):
    kwargs = {
        'measurement_units_data': dbaccessor.get('measurement_units'),
        'hg_params_data': dbaccessor.get('hg_params'),
        }
    data = [{
        'hg_param_name': None,
        'hg_param_value': None,
        'meas_units_abb': None
        }]

    # The hg_param_name is not valid.
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_params_data_imported_data('survey_test', data, **kwargs)
    assert excinfo.value.code == 301

    # The hg_param_name is not found.
    data[0]['hg_param_name'] = 'no match dummy'

    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_params_data_imported_data('survey_test', data, **kwargs)
    assert excinfo.value.code == 302

    data[0]['hg_param_name'] = 'param in-situ #2'

    # The meas_units_abb is not found.
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_params_data_imported_data('survey_test', data, **kwargs)
    assert excinfo.value.code == 303

    data[0]['meas_units_abb'] = '‰'

    # The hg_param_value is None.
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_params_data_imported_data('survey_test', data, **kwargs)
    assert excinfo.value.code == 304

    # The hg_param_value is not valid.
    data[0]['hg_param_value'] = 'dummy'

    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_params_data_imported_data('survey_test', data, **kwargs)
    assert excinfo.value.code == 304

    data[0]['hg_param_value'] = '< 304'

    # The next call should not raise any error.
    fmt_data = format_params_data_imported_data('survey_test', data, **kwargs)
    assert fmt_data == [{
        'hg_survey_id': 'survey_test',
        'hg_param_id': 2,
        'meas_units_id': 3,
        'hg_param_value': '< 304'
        }]


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
