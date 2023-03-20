# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Local imports
from sardes.api.tablemodels import (
    SardesTableColumn, sardes_table_column_factory)
from sardes.config.locale import _
from sardes.tables.models import StandardSardesTableModel
from sardes.widgets.tableviews import SardesTableWidget
from sardes.tables.delegates import (
    IntEditDelegate, DateTimeDelegate, NumEditDelegate, StringEditDelegate,
    GenericLibSelectDelegate)


class PurgesTableModel(StandardSardesTableModel):
    """
    A table model to display a list of pump types that
    are available to use in the HG Parameters table.
    """
    __tablename__ = 'table_purges'
    __tabletitle__ = _('Purges')
    __tablecolumns__ = [
        SardesTableColumn(
            'survey_well_id', _('Well ID'), 'str',
            delegate=StringEditDelegate),
        sardes_table_column_factory(
            'purges', 'hg_survey_id', _('Survey Date/Time'),
            delegate=IntEditDelegate),
        sardes_table_column_factory(
            'purges', 'purge_sequence_no', _('Sequence No.'),
            delegate=IntEditDelegate),
        sardes_table_column_factory(
            'purges', 'purge_seq_start', _('Date/Time Start'),
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd hh:mm"}),
        sardes_table_column_factory(
            'purges', 'purge_seq_end', _('Date/Time End'),
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd hh:mm"}),
        sardes_table_column_factory(
            'purges', 'purge_outflow', _('Outflow (L/min)'),
            delegate=NumEditDelegate,
            delegate_options={
                'decimals': 3, 'minimum': 0, 'maximum': 99999}),
        sardes_table_column_factory(
            'purges', 'pump_type_id', _('Pump Type'),
            delegate=GenericLibSelectDelegate,
            delegate_options={
                'lib_name': 'pump_types',
                'lib_column_name': 'pump_type_name'}),
        sardes_table_column_factory(
            'purges', 'pumping_depth', _('Pumping Depth (m)'),
            delegate=NumEditDelegate,
            delegate_options={
                'decimals': 3, 'minimum': 0, 'maximum': 99999}),
        sardes_table_column_factory(
            'purges', 'static_water_level', _('Static Water Level (mbgs)'),
            delegate=NumEditDelegate,
            delegate_options={
                'decimals': 3, 'minimum': 0, 'maximum': 99999}),
        ]

    __dataname__ = 'purges'
    __libnames__ = ['pump_types', 'hg_surveys']


class PurgesTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = PurgesTableModel()
        super().__init__(table_model, *args, **kargs)
