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
    ObsWellIdEditDelegate, TextEditDelegate, StringEditDelegate,
    DateTimeDelegate, GenericLibSelectDelegate)


class RemarksTableModel(StandardSardesTableModel):
    """
    A table model to display a list of remarks related to monitoring
    data over a given period.
    """
    __tablename__ = 'table_remarks'
    __tabletitle__ = _('Remarks')
    __tablecolumns__ = [
        sardes_table_column_factory(
            'remarks', 'sampling_feature_uuid', _('Well ID'),
            delegate=ObsWellIdEditDelegate
            ),
        sardes_table_column_factory(
            'remarks', 'remark_type_id', _('Type'),
            delegate=GenericLibSelectDelegate,
            delegate_options={
                'lib_name': 'remark_types',
                'lib_column_name': 'remark_type_name'}
            ),
        sardes_table_column_factory(
            'remarks', 'period_start', _('Date From'),
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd hh:mm"},
            ),
        sardes_table_column_factory(
            'remarks', 'period_end', _('Date To'),
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd hh:mm"},
            ),
        sardes_table_column_factory(
            'remarks', 'remark_text', _('Remark'),
            delegate=TextEditDelegate
            ),
        sardes_table_column_factory(
            'remarks', 'remark_author', _('Auteur'),
            delegate=StringEditDelegate
            ),
        sardes_table_column_factory(
            'remarks', 'remark_date', _('Date'),
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd"},
            )
        ]

    __dataname__ = 'remarks'
    __libnames__ = ['remark_types', 'observation_wells_data']


class RemarksTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = RemarksTableModel()
        super().__init__(table_model, *args, **kargs)
