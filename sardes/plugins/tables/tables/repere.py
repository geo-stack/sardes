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
from sardes.api.tablemodels import StandardSardesTableModel, SardesTableColumn
from sardes.config.locale import _
from sardes.widgets.tableviews import (
    SardesTableWidget, BoolEditDelegate, NotEditableDelegate, TextEditDelegate,
    DateTimeDelegate, NumEditDelegate)
from sardes.plugins.tables.tables.delegates import ObsWellIdEditDelegate


class RepereTableModel(StandardSardesTableModel):
    """
    A table model to display the repere data related to the observation
    wells of the monitoring network.
    """
    __tablecolumns__ = [
        SardesTableColumn(
            'sampling_feature_uuid', _('Well ID'), 'str', notnull=True),
        SardesTableColumn(
            'top_casing_alt', _('Top Casing Alt. (m)'), 'float64',
            notnull=True),
        SardesTableColumn(
            'casing_length', _('Length Casing (m)'), 'float64', notnull=True),
        SardesTableColumn(
            'start_date', _('Date From'), 'datetime64[ns]', notnull=True),
        SardesTableColumn(
            'end_date', _('Date To'), 'datetime64[ns]'),
        SardesTableColumn(
            'is_alt_geodesic', _('Geodesic'), 'boolean', notnull=True),
        SardesTableColumn(
            'repere_note', _('Notes'), 'str')
        ]

    def create_delegate_for_column(self, view, column):
        """
        Create the item delegate that the view need to use when editing the
        data of this model for the specified column. If None is returned,
        the items of the column will not be editable.
        """
        if column in ['sampling_feature_uuid']:
            return ObsWellIdEditDelegate(view, is_required=True)
        elif column in ['top_casing_alt', 'casing_length']:
            return NumEditDelegate(view, decimals=3, bottom=-99999, top=99999,
                                   is_required=True)
        elif column in ['start_date']:
            return DateTimeDelegate(view, is_required=True,
                                    display_format="yyyy-MM-dd hh:mm")
        elif column in ['end_date']:
            return DateTimeDelegate(view, display_format="yyyy-MM-dd hh:mm")
        elif column in ['is_alt_geodesic']:
            return BoolEditDelegate(view, is_required=True)
        elif column in ['repere_note']:
            return TextEditDelegate(view, is_required=False)
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
                .map(obs_wells_data['obs_well_id'].to_dict().get)
                )
        except KeyError:
            pass

        visual_dataf['start_date'] = (
            pd.to_datetime(visual_dataf['start_date'], format="%Y-%m-%d %H:%M")
            .dt.strftime('%Y-%m-%d %H:%M'))
        visual_dataf['end_date'] = (
            pd.to_datetime(visual_dataf['end_date'], format="%Y-%m-%d %H:%M")
            .dt.strftime('%Y-%m-%d %H:%M'))
        visual_dataf['is_alt_geodesic'] = (
            visual_dataf['is_alt_geodesic']
            .map({True: _('Yes'), False: _('No')}.get)
            )
        return visual_dataf


class RepereTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = RepereTableModel(
            table_title=_('Repere'),
            table_id='table_repere')
        super().__init__(table_model, *args, **kargs)
