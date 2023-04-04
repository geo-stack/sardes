# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""Fixtures for the database Accessors."""


# ---- Standard imports
from datetime import datetime, date
import os.path as osp
from random import randrange
import uuid
from uuid import UUID

# ---- Third party imports
import xlsxwriter
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import pandas as pd
import pytest

# ---- Local imports
from sardes.api.timeseries import DataType


@pytest.fixture
def obswells_data():
    data = [
        ['03037041', "St-Paul-d'Abbotsford", "Saint-Paul-d'Abbotsford",
         'MT', 'Confined', 3, 0, 0,
         45.445178, -72.828773, True, 'Note for well 03037041'],
        ['02200001', "Réserve de Duchénier", "Saint-Narcisse-de-Rimouski",
         'ROC', 'Unconfined', 2, 1, 0,
         48.20282, -68.52795, True, None],
        ['02167001', 'Matane', 'Matane',
         'MT', 'Captive', 3, 2, 2,
         48.81151, -67.53562, True, None],
        ['03040002', 'PO-01', 'Calixa-Lavallée',
         'ROC', 'Confined', 1, 0, 0,
         45.74581, -73.28024, True, None],
        ['09000001', 'Site 1', 'Umiujaq',
         'MT', 'Libre', 4, 1, 0,
         56.56248, -76.47886, False, None]
        ]
    df = pd.DataFrame(
        data=data,
        index=[UUID('3c6d0e15-6775-4304-964a-5db89e463c55'),
               UUID('dcc36634-ae7e-42c0-966d-77f575232ead'),
               UUID('f61556e8-13a1-43c7-9fbb-aec4d9b0a369'),
               UUID('f9b519b8-2d86-44cf-ba97-61427e30398f'),
               UUID('e23753a9-c13d-44ac-9c13-8b7e1278075f')],
        columns=['obs_well_id', 'common_name', 'municipality',
                 'aquifer_type', 'confinement', 'aquifer_code',
                 'in_recharge_zone', 'is_influenced', 'latitude',
                 'longitude', 'is_station_active', 'obs_well_notes']
        )
    df.attrs['name'] = 'observation_wells_data'
    return df


@pytest.fixture
def repere_data(obswells_data):
    data = [
        [obswells_data.index[0], 9.3, 1.3,
         datetime(2009, 7, 14, 9), datetime(2020, 8, 3, 19, 14),
         True, 'Repere note #1'],
        [obswells_data.index[1], 64.49, 1.49,
         datetime(2005, 11, 9, 13), None,
         True, 'Repere note #2'],
        [obswells_data.index[2], 41.251, 0.94,
         datetime(2009, 7, 14, 19), None,
         False, 'Repere note #3'],
        [obswells_data.index[3], 400.35, 0.35,
         datetime(2009, 11, 14, 13), None,
         False, 'Repere note #4'],
        [obswells_data.index[4], 26.6, -0.6,
         datetime(2008, 11, 20, 1, 25), None,
         True, 'Repere note #5']
        ]
    df = pd.DataFrame(
        data,
        index=[uuid.uuid4() for row in data],
        columns=['sampling_feature_uuid', 'top_casing_alt', 'casing_length',
                 'start_date', 'end_date', 'is_alt_geodesic', 'repere_note']
        )
    df.attrs['name'] = 'repere_data'
    return df


@pytest.fixture
def manual_measurements(obswells_data):
    data = [
        [obswells_data.index[0], datetime(2010, 8, 10, 16, 10, 34), 5.23,
         'Note first measurement'],
        [obswells_data.index[0], datetime(2010, 11, 10, 12, 55, 22), 4.36, ''],
        [obswells_data.index[0], datetime(2011, 8, 2, 18, 50, 17), 4.91,
         'Note third measurement'],
        [obswells_data.index[1], datetime(2009, 8, 2, 18, 34, 38), 28.34, ''],
        [obswells_data.index[2], datetime(2015, 8, 2, 18, 37, 23), 14.87, ''],
        [obswells_data.index[2], datetime(2016, 2, 4, 13, 26, 3), 2.03, '']]
    df = pd.DataFrame(
        data,
        index=[uuid.uuid4() for row in data],
        columns=['sampling_feature_uuid', 'datetime', 'value', 'notes']
        )
    df.attrs['name'] = 'manual_measurements'
    return df


@pytest.fixture
def sonde_models():
    df = pd.DataFrame(
        [['Solinst', 'Barologger M1.5 Gold'],
         ['Solinst', 'LT M10 Gold'],
         ['Solinst', 'LT M10 Edge'],
         ['Solinst', 'Barologger M1.5'],
         ['Solinst', 'LT M10'],
         ['Solinst', 'LT M20 Gold'],
         ['Solinst', 'L M10'],
         ['Telog 1', 'Druck'],
         ['Telog 2', 'Druck'],
         ['In-Situ', 'Troll']],
        columns=['sonde_brand', 'sonde_model']
        )
    df.attrs['name'] = 'sonde_models'
    return df


@pytest.fixture
def sondes_data():
    data = [
        [5, '1016042', datetime(2006, 3, 30), datetime(2020, 12, 31),
         False, False, False, False, 'Note sonde 1016042.'],
        [5, '1031928', datetime(2008, 6, 4), pd.NaT,
         False, False, False, False, None],
        [5, '1021777', datetime(2007, 3, 26), pd.NaT,
         False, False, False, False, None],
        [1, '1016387', datetime(2006, 3, 30), datetime(2020, 12, 31),
         False, False, False, False, None],
        [4, '1060487', datetime(2012, 5, 5), pd.NaT,
         False, False, False, False, None],
        [1, '1048409', datetime(2010, 2, 8), pd.NaT,
         False, False, False, False, None],
        ]
    df = pd.DataFrame(
        data,
        index=[UUID('3b8f4a6b-14d0-461e-8f1a-08a5ea465a1e'),
               UUID('dd4435b1-8699-4694-a303-5ca9b9bff111'),
               UUID('776ca385-cf2c-4afe-a7d6-559ffa0e2735'),
               UUID('e8e9782c-773a-48ba-9f4d-a7253e2642ee'),
               UUID('ae2d95ee-e3b6-40c9-9628-fe0833b3dd37'),
               UUID('f9d0dbb6-6379-49f8-8473-59bc8007e20d')],
        columns=['sonde_model_id', 'sonde_serial_no',
                 'date_reception', 'date_withdrawal', 'in_repair',
                 'out_of_order', 'lost', 'off_network', 'sonde_notes']
        )
    df.attrs['name'] = 'sondes_data'
    return df


@pytest.fixture
def sondes_installation(obswells_data, sondes_data):
    data = [
        [datetime(2006, 8, 24, 18), datetime(2020, 12, 31, 7, 14), 9.02,
         obswells_data.index[0], sondes_data.index[0],
         'Note for first sonde installation.'],
        [datetime(2009, 7, 24, 19), datetime(2020, 12, 31), 7.19,
         obswells_data.index[1], sondes_data.index[1], None],
        [datetime(2007, 11, 14, 19), pd.NaT, 10.1,
         obswells_data.index[2], sondes_data.index[2], None],
        [datetime(2007, 11, 14, 19), pd.NaT, 2.0,
         obswells_data.index[2], sondes_data.index[3], None],
        [datetime(2012, 5, 5, 19), pd.NaT, 9.24,
         obswells_data.index[3], sondes_data.index[4], None],
        [datetime(2012, 5, 5, 19), pd.NaT, 1.0,
         obswells_data.index[3], sondes_data.index[5], None]
        ]
    df = pd.DataFrame(
        data,
        index=[
            UUID('a540e969-a950-41c1-846f-1f9d2ea86ade'),
            UUID('b71d5f2d-a1cf-474d-bc35-b827090f1998'),
            UUID('646bbc29-f02c-437a-b3cf-e985cc39f154'),
            UUID('d4c37ded-090b-4d8b-8724-fc03b7d4d427'),
            UUID('bab4e1c1-3d87-4fe2-922c-f33ac25baf30'),
            UUID('559831cb-012a-4f97-9eef-5b84b4e3869d')],
        columns=['start_date', 'end_date', 'install_depth',
                 'sampling_feature_uuid', 'sonde_uuid', 'install_note']
        )
    df.attrs['name'] = 'sonde_installations'
    return df


@pytest.fixture
def remark_types():
    df = pd.DataFrame(
        [['C', 'Correction', 'Correction made on the monitoring data.'],
         ['U', 'Uncertainty', 'Uncertainty of the monitoring data.']],
        columns=['remark_type_code', 'remark_type_name', 'remark_type_desc']
        )
    df.attrs['name'] = 'remark_types'
    return df


@pytest.fixture
def remarks(obswells_data):
    data = [
        [obswells_data.index[0], 1,
         datetime(2011, 8, 24, 18), datetime(2012, 2, 5, 6, 15),
         "text_remark_1", "author_remark_1", datetime(2022, 6, 23, 6, 15)],
        [obswells_data.index[2], 2,
         datetime(2014, 3, 12), datetime(2014, 6, 6),
         "text_remark_2", "author_remark_2", datetime(2021, 9, 2)],
        ]
    df = pd.DataFrame(
        data,
        columns=['sampling_feature_uuid', 'remark_type_id',
                 'period_start', 'period_end',
                 'remark_text', 'remark_author', 'remark_date']
        )
    df.attrs['name'] = 'remarks'
    return df


@pytest.fixture
def readings_data():
    readings_data = pd.DataFrame(
        [], columns=['datetime', DataType.WaterLevel, DataType.WaterTemp])
    readings_data['datetime'] = pd.date_range(
        start='1/1/2015', end='31/12/2020')
    readings_data[DataType.WaterLevel] = np.random.rand(len(readings_data)) + 1
    readings_data[DataType.WaterTemp] = np.random.rand(len(readings_data)) * 10
    readings_data[DataType.WaterEC] = np.random.rand(len(readings_data)) + 100
    return readings_data


@pytest.fixture
def constructlog(tmp_path):
    # Note: we cannot use pyplot direectly or we encounter issues with pytest.
    figure = Figure()
    canvas = FigureCanvasAgg(figure)
    ax = figure.add_axes([0.1, 0.1, 0.8, 0.8], frameon=True)
    ax.plot([1, 2, 3, 4])

    filename = osp.join(tmp_path, 'constructlog_testfile.pdf')
    figure.savefig(filename)

    return filename


@pytest.fixture
def measurement_units():
    df = pd.DataFrame(
        data=[['µg/L', 'units name #1', 'desc units #1'],
              ['µmhos/cm', 'units name #2', 'desc units #2'],
              ['‰', 'units name #2', 'desc units #3']],
        index=[1, 2, 3],
        columns=['meas_units_abb', 'meas_units_name', 'meas_units_desc']
        )
    df.attrs['name'] = 'measurement_units'
    return df


@pytest.fixture
def pump_types():
    df = pd.DataFrame(
        data=[['PUMP#1', 'Pump type #1 desc'],
              ['PUMP#2', 'Pump type #2 desc'],
              ['PUMP#3', 'Pump type #3 desc'],
              ['PUMP#4', 'Pump type #4 desc'],
              ['PUMP#5', 'Pump type #5 desc']],
        index=[1, 2, 3, 4, 5],
        columns=['pump_type_name', 'pump_type_desc']
        )
    df.attrs['name'] = 'pump_types'
    return df


@pytest.fixture
def hg_params():
    df = pd.DataFrame(
        data=[['PARAM#1', 'Name param #1', 'PARAM#1 Regex', '111-0-11'],
              ['PARAM#2', 'Name param #2', 'PARAM#2 Regex', '22-0-23'],
              ['PARAM#3', 'Name param #3', 'PARAM#3 Regex', '34-5-12'],
              ['PARAM#4', 'Name param #4', 'PARAM#4 Regex', '73-2-9']],
        index=[1, 2, 3, 4],
        columns=['hg_param_code', 'hg_param_name', 'hg_param_regex',
                 'cas_registry_number']
        )
    df.attrs['name'] = 'hg_params'
    return df


@pytest.fixture
def hg_sampling_methods():
    df = pd.DataFrame(
        data=[['Method #1', 'Desc. Methode #1.'],
              ['Method #2', 'Desc. Methode #2.'],
              ['Method #3', 'Desc. Methode #3.']],
        index=[1, 2, 3],
        columns=['hg_sampling_method_name', 'hg_sampling_method_desc']
        )
    df.attrs['name'] = 'hg_sampling_methods'
    return df


@pytest.fixture
def hg_surveys(obswells_data):
    df = pd.DataFrame(
        data=[[obswells_data.index[0], datetime(2011, 8, 2, 15, 20), 10.23,
               'Operator survey #1', 2, 1, 'Note survey #1'],
              [obswells_data.index[0], datetime(2015, 5, 3, 12, 45), 5.14,
               'Operator survey #2', 3, 0, 'Note survey #2'],
              [obswells_data.index[0], datetime(2017, 6, 1), None,
               None, None, 2, 'Note survey #3'],
              [obswells_data.index[2], datetime(2019, 9, 9), None,
               'Operator survey #4', None, None, None]
              ],
        index=[1, 2, 3, 4],
        columns=['sampling_feature_uuid', 'hg_survey_datetime',
                 'hg_survey_depth', 'hg_survey_operator',
                 'hg_sampling_method_id', 'sample_filtered',
                 'survey_note']
        )
    df.attrs['name'] = 'hg_surveys'
    return df


@pytest.fixture
def hg_labs():
    df = pd.DataFrame(
        data=[['lab#1', 'lab_num_one', 'contacts#1'],
              ['lab#2', 'lab_num_two', 'contacts#2'],
              ],
        index=[1, 2],
        columns=['lab_code', 'lab_name', 'lab_contacts']
        )
    df.attrs['name'] = 'hg_labs'
    return df


@pytest.fixture
def hg_param_values():
    df = pd.DataFrame(
        data=[[1, 3, '> 0.345', 0.345, 1, 'Sample#1', 1,
               datetime(2017, 11, 15, 4, 15), 'Method #1', 'Note #1'],
              [1, 1, '0.867', 0.123, None, 'Sample#1', 1,
               datetime(2017, 11, 15, 4, 15), 'Method #2', 'Note #2'],
              [1, 4, '-0.54', 0.25, 2, 'Sample#1', 2,
               datetime(2017, 11, 15, 4, 15), 'Method #3', 'Note #3'],
              [2, 1, '1.345', 1.25, 3, None, None,
               None, None, None],
              ],
        index=[1, 2, 3, 4],
        columns=['hg_survey_id', 'hg_param_id', 'hg_param_value',
                 'lim_detection', 'meas_units_id', 'lab_sample_id',
                 'lab_id', 'lab_report_date', 'method', 'notes']
        )
    df.attrs['name'] = 'hg_param_values'
    return df


@pytest.fixture
def purges():
    df = pd.DataFrame(
        data=[[1, 1,
               datetime(2011, 8, 2, 14, 7), datetime(2011, 8, 2, 14, 25),
               8.5, 2, 7.86, 4.57],
              [1, 2,
               datetime(2011, 8, 2, 14, 25), datetime(2011, 8, 2, 15, 20),
               8.0, 2, 7.86, 4.57],
              [4, 1,
               datetime(2011, 8, 2, 14, 25), datetime(2011, 8, 2, 15, 20),
               8.0, 5, None, None]],
        index=[1, 2, 3],
        columns=['hg_survey_id', 'purge_sequence_no', 'purge_seq_start',
                 'purge_seq_end', 'purge_outflow', 'pump_type_id',
                 'pumping_depth', 'water_level_drawdown']
        )
    df.attrs['name'] = 'purges'
    return df


@pytest.fixture
def database_filler(
        obswells_data, constructlog, readings_data, repere_data,
        manual_measurements, sondes_data, sondes_installation, remark_types,
        remarks, measurement_units, hg_params, hg_sampling_methods, hg_surveys,
        hg_param_values, pump_types, purges, hg_labs):

    def fill_database(dbaccessor):
        # Add tables with 'uuid' indexes to the database.
        for df in [obswells_data, repere_data, sondes_data,
                   sondes_installation, manual_measurements]:
            _dict = df.to_dict('index')
            dbaccessor.add(
                name=df.attrs['name'],
                values=_dict.values(),
                indexes=_dict.keys()
                )
        # Add table with 'int' indexes to the database.
        for df in [remarks, remark_types, measurement_units, hg_params,
                   hg_sampling_methods, hg_surveys, hg_param_values,
                   pump_types, purges, hg_labs]:
            _dict = df.to_dict('index')
            dbaccessor.add(
                name=df.attrs['name'],
                values=_dict.values(),
                )

        # Add attachments and monitoring data.
        for obs_well_uuid, obs_well_data in obswells_data.iterrows():
            if obs_well_data['obs_well_id'] == '09000001':
                # We don't want to add any attachment or monitoring data
                # to that well.
                continue

            # Add a construction log.
            dbaccessor.set_attachment(obs_well_uuid, 1, constructlog)

            # Add timeseries data.
            if obs_well_uuid == obswells_data.index[0]:
                install_uuid = sondes_installation.index[0]
            else:
                install_uuid = None
            dbaccessor.add_timeseries_data(
                readings_data, obs_well_uuid, install_uuid)

    return fill_database
