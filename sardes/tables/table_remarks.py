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
    DateTimeDelegate, RemarkTypeEditDelegate)


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
            delegate=ObsWellIdEditDelegate),
        sardes_table_column_factory(
            'remarks', 'remark_type_id', _('Type'),
            delegate=RemarkTypeEditDelegate
            ),
        sardes_table_column_factory(
            'remarks', 'period_start', _('Date From'),
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd hh:mm"},
            strftime_format='%Y-%m-%d %H:%M'
            ),
        sardes_table_column_factory(
            'remarks', 'period_end', _('Date To'),
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd hh:mm"},
            strftime_format='%Y-%m-%d %H:%M'
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
            strftime_format='%Y-%m-%d'
            )
        ]

    __dataname__ = 'remarks'
    __libnames__ = ['remark_types', 'observation_wells_data']

    # ---- Visual Data
    def logical_to_visual_data(self, visual_dataf):
        """
        Transform logical data to visual data.
        """
        try:
            obs_wells_data = self.libraries['observation_wells_data']
            visual_dataf['sampling_feature_uuid'] = (
                visual_dataf['sampling_feature_uuid']
                .map(obs_wells_data['obs_well_id'].to_dict().get)
                )
        except KeyError:
            pass
        try:
            remark_types = self.libraries['remark_types']
            visual_dataf['remark_type_id'] = (
                visual_dataf['remark_type_id']
                .map(remark_types['remark_type_name'].to_dict().get)
                )
        except KeyError:
            pass
        return super().logical_to_visual_data(visual_dataf)


class RemarksTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = RemarksTableModel()
        super().__init__(table_model, *args, **kargs)
