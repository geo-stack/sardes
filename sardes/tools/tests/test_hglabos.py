# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the HG survey import tool basic function.

Note that the tool is tested in test_table_hg_param_values.py
"""

# ---- Standard imports
import os
import os.path as osp
import datetime as dtm
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pytest

# ---- Local imports
from sardes import __rootdir__
from sardes.database.accessors.accessor_errors import ImportHGSurveysError
from sardes.tools.hglabos import read_hglab_data, format_hglab_data


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
            'lab_report_date': dtm.datetime(2023, 6, 19),
            'lab_code': '0105',
            'obs_well_id': '03037041',
            'hg_survey_datetime': dtm.datetime(2011, 8, 2, 15, 20),
            'lab_sample_id': 'ech001',
            'hg_param_expr': 'param 1',
            'hg_param_value': '0.34',
            'lim_detection': 0.11,
            'meas_units_abb': 'µg/L',
            'method': 'méthode #1',
            'notes': 'note param #1',
            }
        assert data_report[1] == {
            'lab_report_date': dtm.datetime(2023, 6, 19),
            'lab_code': '0105',
            'obs_well_id': '03037041',
            'hg_survey_datetime': dtm.datetime(2011, 8, 2, 15, 20),
            'lab_sample_id': None,
            'hg_param_expr': 'param 2',
            'hg_param_value': '< 0.12',
            'lim_detection': 0.12,
            'meas_units_abb': None,
            'method': 'méthode #1',
            'notes': None,
            }
        assert data_report[2] == {
            'lab_report_date': dtm.datetime(2023, 6, 19),
            'lab_code': '0105',
            'obs_well_id': '02167001',
            'hg_survey_datetime': dtm.datetime(2019, 9, 9),
            'lab_sample_id': 'ech002',
            'hg_param_expr': 'param 3',
            'hg_param_value': None,
            'lim_detection': None,
            'meas_units_abb': '‰',
            'method': None,
            'notes': 'note param #3',
            }


def test_format_hglab_data(dbaccessor):
    """
    Test that formatting imported HG survey data is working as expected.
    """
    kwargs = {
        'observation_wells_data': dbaccessor.get('observation_wells_data'),
        'hg_surveys_data': dbaccessor.get('hg_surveys'),
        'hg_params_data': dbaccessor.get('hg_params'),
        'measurement_units_data': dbaccessor.get('measurement_units'),
        'hg_labs_data': dbaccessor.get('hg_labs'),
        }
    all_lab_reports = {}
    all_lab_reports['report #1'] = [
        {'lab_report_date': 'dummy',
         'lab_code': 'dummy',
         'obs_well_id': None,
         'hg_survey_datetime': None,
         'lab_sample_id': 1234567890,
         'hg_param_expr': None,
         'hg_param_value': None,
         'lim_detection': 'dummy',
         'meas_units_abb': None,
         'method': 1234567890,
         'notes': 1234567890},
        # Valid param entry with no None values.
        {'lab_report_date': dtm.datetime(2023, 6, 19),
         'lab_code': 'lab#1',
         'obs_well_id': '03037041',
         'hg_survey_datetime': dtm.datetime(2011, 8, 2, 15, 20),
         'lab_sample_id': 'sample #1',
         'hg_param_expr': 'param 2',
         'hg_param_value': '< 0.12',
         'lim_detection': 0.12,
         'meas_units_abb': 'µg/L',
         'method': 'méthode #1',
         'notes': 'test note'}
        ]
    # Valid param entry with None values.
    all_lab_reports['report #2'] = [
        {'lab_report_date': None,
         'lab_code': None,
         'obs_well_id': '02167001',
         'hg_survey_datetime': dtm.datetime(2019, 9, 9),
         'lab_sample_id': None,
         'hg_param_expr': 'param 3',
         'hg_param_value': '0.03',
         'lim_detection': None,
         'meas_units_abb': '‰',
         'method': None,
         'notes': None}
        ]

    # Work through all expected error that could be
    # raised in the tested function for the required attributes.

    # The lab_report_date is not valid.
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_hglab_data(all_lab_reports, **kwargs)
    assert excinfo.value.code == 401

    all_lab_reports['report #1'][0]['lab_report_date'] = (
        dtm.datetime(2023, 6, 19))

    # The lab_code is not valid.
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_hglab_data(all_lab_reports, **kwargs)
    assert excinfo.value.code == 402

    all_lab_reports['report #1'][0]['lab_code'] = 'lab#1'

    # The obs_well_id is None.
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_hglab_data(all_lab_reports, **kwargs)
    assert excinfo.value.code == 403

    # The obs_well_id does not exist.
    all_lab_reports['report #1'][0]['obs_well_id'] = '12345'
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_hglab_data(all_lab_reports, **kwargs)
    assert excinfo.value.code == 403

    all_lab_reports['report #1'][0]['obs_well_id'] = '03037041'

    # The hg_survey_datetime is not valid.
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_hglab_data(all_lab_reports, **kwargs)
    assert excinfo.value.code == 404

    # The hg_survey_id cannot be found.
    all_lab_reports['report #1'][0]['hg_survey_datetime'] = (
        dtm.datetime(2020, 8, 2, 15, 20))
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_hglab_data(all_lab_reports, **kwargs)
    assert excinfo.value.code == 405

    all_lab_reports['report #1'][0]['hg_survey_datetime'] = (
        dtm.datetime(2011, 8, 2, 15, 20))

    # The meas_units_id cannot be found.
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_hglab_data(all_lab_reports, **kwargs)
    assert excinfo.value.code == 406

    all_lab_reports['report #1'][0]['meas_units_abb'] = 'µmhos/cm'

    # The hg_param_value is None.
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_hglab_data(all_lab_reports, **kwargs)
    assert excinfo.value.code == 407

    # The hg_param_value is not valid.
    all_lab_reports['report #1'][0]['hg_param_value'] = 'l 305'
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_hglab_data(all_lab_reports, **kwargs)
    assert excinfo.value.code == 407

    all_lab_reports['report #1'][0]['hg_param_value'] = '305'

    # The lim_detection is not valid.
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_hglab_data(all_lab_reports, **kwargs)
    assert excinfo.value.code == 408

    all_lab_reports['report #1'][0]['lim_detection'] = 305

    # The hg_param_id is None.
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_hglab_data(all_lab_reports, **kwargs)
    assert excinfo.value.code == 409

    # The hg_param_id is cannot be found.
    all_lab_reports['report #1'][0]['hg_param_expr'] = 'dummy'
    with pytest.raises(ImportHGSurveysError) as excinfo:
        format_hglab_data(all_lab_reports, **kwargs)
    assert excinfo.value.code == 410

    all_lab_reports['report #1'][0]['hg_param_expr'] = 'param 1'

    # The next call should not raise any error.
    fmt_hglab_data = format_hglab_data(all_lab_reports, **kwargs)

    assert len(fmt_hglab_data) == 3
    assert fmt_hglab_data[0] == {
        'lab_report_date': dtm.datetime(2023, 6, 19),
        'lab_id': 1,
        'hg_survey_id': 1,
        'lab_sample_id': '1234567890',
        'meas_units_id': 2,
        'notes': '1234567890',
        'hg_param_id': 1,
        'hg_param_value': '305',
        'lim_detection': 305,
        'method': '1234567890'
        }
    assert fmt_hglab_data[1] == {
        'lab_report_date': dtm.datetime(2023, 6, 19),
        'lab_id': 1,
        'hg_survey_id': 1,
        'lab_sample_id': 'sample #1',
        'meas_units_id': 1,
        'notes': 'test note',
        'hg_param_id': 2,
        'hg_param_value': '< 0.12',
        'lim_detection': 0.12,
        'method': 'méthode #1'
        }
    assert fmt_hglab_data[2] == {
        'lab_report_date': None,
        'lab_id': None,
        'hg_survey_id': 4,
        'lab_sample_id': None,
        'meas_units_id': 3,
        'notes': None,
        'hg_param_id': 3,
        'hg_param_value': '0.03',
        'lim_detection': None,
        'method': None,
        'notes': None
        }


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
