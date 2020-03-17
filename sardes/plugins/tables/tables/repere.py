# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Thirs party imports
import pandas as pd

# ---- Local imports
from sardes.api.tablemodels import SardesTableModel
from sardes.config.locale import _
from sardes.widgets.tableviews import (
    SardesTableWidget, BoolEditDelegate, NotEditableDelegate, TextEditDelegate,
    DateTimeDelegate, NumEditDelegate)
from sardes.plugins.tables.tables.delegates import ObsWellIdEditDelegate


class RepereTableModel(SardesTableModel):
    """
    A table model to display the repere data related to the observation
    wells of the monitoring network.
    """

    def create_delegate_for_column(self, view, column):
        """
        Create the item delegate that the view need to use when editing the
        data of this model for the specified column. If None is returned,
        the items of the column will not be editable.
        """
        if column in ['sampling_feature_uuid']:
            return ObsWellIdEditDelegate(view, is_required=True)
        elif column == 'top_casing_alt':
            return NumEditDelegate(view, decimals=3, bottom=-99999, top=99999)
        elif column == 'casing_length':
            return NumEditDelegate(view, decimals=3, bottom=0, top=99999)
        elif column in ['start_date']:
            return DateTimeDelegate(view, is_required=True,
                                    display_format="yyyy-MM-dd hh:mm")
        elif column in ['end_date']:
            return DateTimeDelegate(view, display_format="yyyy-MM-dd hh:mm")
        elif column in ['is_alt_geodesic']:
            return BoolEditDelegate(view, is_required=True)
        elif column in ['repere_note']:
            return TextEditDelegate(view, is_required=True)
        else:
            return NotEditableDelegate(view)

    # ---- Visual Data
    def logical_to_visual_data(self, visual_dataf):
        """
        Transform logical data to visual data.
        """
        try:
            obs_wells_data = self.libraries['observation_wells_data']
            visual_dataf['sampling_feature_uuid'] = (
                visual_dataf['sampling_feature_uuid']
                .replace(obs_wells_data['obs_well_id'].to_dict())
                )
        except KeyError:
            pass

        visual_dataf['start_date'] = (
            pd.to_datetime(visual_dataf['start_date'], format="%Y-%m-%d %H:%M")
            .dt.strftime('%Y-%m-%d %H:%M'))
        visual_dataf['end_date'] = (
            pd.to_datetime(visual_dataf['end_date'], format="%Y-%m-%d %H:%M")
            .dt.strftime('%Y-%m-%d %H:%M'))
        return visual_dataf


class RepereTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = RepereTableModel(
            table_title=_('Repere'),
            table_id='table_repere',
            data_columns_mapper=[
                ('sampling_feature_uuid', _('Well')),
                ('top_casing_alt', _('Top Casing Alt. (m)')),
                ('casing_length', _('Length Casing (m)')),
                ('start_date', _('Date From')),
                ('end_date', _('Date To')),
                ('is_alt_geodesic', _('Geodesic')),
                ('repere_note', _('Notes')),
                ]
            )
        super().__init__(table_model, *args, **kargs)