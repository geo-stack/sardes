# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Local imports
from sardes.api.tablemodels import sardes_table_column_factory
from sardes.config.locale import _
from sardes.tables.models import StandardSardesTableModel
from sardes.widgets.tableviews import SardesTableWidget
from sardes.tables.delegates import (
    StringEditDelegate, NumEditDelegate, DateTimeDelegate,
    TextEditDelegate, GenericLibSelectDelegate, HGSurveyEditDelegate)


class HGParamValuesTableModel(StandardSardesTableModel):
    """
    A table model to display the values of the measured
    hydrogeochemical parameters.
    """
    __tablename__ = 'table_hg_param_values'
    __tabletitle__ = _('HG Values')
    __tablecolumns__ = [
        sardes_table_column_factory(
            'hg_param_values', 'hg_survey_id', _('Survey Well ID - Date/Time'),
            delegate=HGSurveyEditDelegate),
        sardes_table_column_factory(
            'hg_param_values', 'hg_param_id', _('Parameter'),
            delegate=GenericLibSelectDelegate,
            delegate_options={
                'lib_name': 'hg_params',
                'lib_column_name': 'hg_param_code'}),
        sardes_table_column_factory(
            'hg_param_values', 'hg_param_value', _('Value'),
            delegate=StringEditDelegate),
        sardes_table_column_factory(
            'hg_param_values', 'lim_detection', _('Lim. Detection'),
            delegate=NumEditDelegate,
            delegate_options={
                'decimals': 3, 'minimum': 0, 'maximum': 99999}),
        sardes_table_column_factory(
            'hg_param_values', 'meas_units_id', _('Units'),
            delegate=GenericLibSelectDelegate,
            delegate_options={
                'lib_name': 'measurement_units',
                'lib_column_name': 'meas_units_abb'}),
        sardes_table_column_factory(
            'hg_param_values', 'lab_sample_id', _('Sample ID'),
            delegate=StringEditDelegate),
        sardes_table_column_factory(
            'hg_param_values', 'lab_report_date', _('Lab Report Date'),
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd"}),
        sardes_table_column_factory(
            'hg_param_values', 'lab_id', _('Lab'),
            delegate=GenericLibSelectDelegate,
            delegate_options={
                'lib_name': 'hg_labs',
                'lib_column_name': 'lab_code'}),
        sardes_table_column_factory(
            'hg_param_values', 'method', _('Method'),
            delegate=StringEditDelegate),
        sardes_table_column_factory(
            'hg_param_values', 'notes', _('Notes'),
            delegate=TextEditDelegate),
        ]

    __dataname__ = 'hg_param_values'
    __libnames__ = ['measurement_units', 'hg_params', 'hg_surveys',
                    'observation_wells_data', 'hg_labs']


class HGParamValuesTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = HGParamValuesTableModel()
        super().__init__(table_model, *args, **kargs)
