# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Local imports
from sardes.api.tablemodels import SardesTableColumn
from sardes.config.locale import _
from sardes.tables.models import StandardSardesTableModel
from sardes.widgets.tableviews import SardesTableWidget
from sardes.tables.delegates import (
    ObsWellIdEditDelegate, TextEditDelegate,
    DateTimeDelegate, RemarkTypeEditDelegate)


class RemarksTableModel(StandardSardesTableModel):
    """
    A table model to display a list of remarks related to monitoring
    data over a given period.
    """
    __tablename__ = 'remarks'
    __tabletitle__ = _('Remarks')
    __tablecolumns__ = [
        SardesTableColumn(
            'sampling_feature_uuid', _('Well ID'), 'str', notnull=True,
            delegate=ObsWellIdEditDelegate),
        SardesTableColumn(
            'remark_type_id', _('Type'), 'str',
            delegate=RemarkTypeEditDelegate
            ),
        SardesTableColumn(
            'period_start', _('Date From'), 'datetime64[ns]',
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd hh:mm"},
            strftime_format='%Y-%m-%d %H:%M'
            ),
        SardesTableColumn(
            'period_end', _('Date To'), 'datetime64[ns]',
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd hh:mm"},
            strftime_format='%Y-%m-%d %H:%M'
            ),
        SardesTableColumn(
            'remark_text', _('Remark'), 'str',
            delegate=TextEditDelegate
            ),
        SardesTableColumn(
            'remark_author', _('Auteur'), 'str',
            ),
        SardesTableColumn(
            'remark_date', _('Date'), 'datetime64[ns]',
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
