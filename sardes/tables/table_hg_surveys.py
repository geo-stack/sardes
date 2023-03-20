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
    IntEditDelegate, DateTimeDelegate, NumEditDelegate, ObsWellIdEditDelegate,
    StringEditDelegate, TextEditDelegate, GenericLibSelectDelegate,
    TriStateEditDelegate)


class HGSurveysTableModel(StandardSardesTableModel):
    """
    A table model to display a list of pump types that
    are available to use in the Surveys table.
    """
    __tablename__ = 'table_hg_surveys'
    __tabletitle__ = _('HG Surveys')
    __tablecolumns__ = [
        sardes_table_column_factory(
            'hg_surveys', 'sampling_feature_uuid', _('Well ID'),
            delegate=ObsWellIdEditDelegate),
        sardes_table_column_factory(
            'hg_surveys', 'hg_survey_datetime', _('Survey Date/Time'),
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd hh:mm"}),
        sardes_table_column_factory(
            'hg_surveys', 'hg_survey_depth', _('Depth (m)'),
            delegate=NumEditDelegate,
            delegate_options={
                'decimals': 3, 'minimum': 0, 'maximum': 99999}),
        sardes_table_column_factory(
            'hg_surveys', 'hg_survey_operator', _('Operator'),
            delegate=StringEditDelegate),
        sardes_table_column_factory(
            'hg_surveys', 'hg_sampling_method_id', _('Sampling Method'),
            delegate=GenericLibSelectDelegate,
            delegate_options={
                'lib_name': 'hg_sampling_methods',
                'lib_column_name': 'hg_sampling_method_name'}),
        sardes_table_column_factory(
            'hg_surveys', 'sample_filtered', _('Sample Filtered'),
            delegate=TriStateEditDelegate),
        sardes_table_column_factory(
            'hg_surveys', 'survey_note', _('Notes'),
            delegate=TextEditDelegate),
        ]

    __dataname__ = 'hg_surveys'
    __libnames__ = ['observation_wells_data', 'hg_sampling_methods']


class HGSurveysTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = HGSurveysTableModel()
        super().__init__(table_model, *args, **kargs)
