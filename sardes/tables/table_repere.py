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
from sardes.api.tablemodels import SardesTableColumn
from sardes.config.locale import _
from sardes.widgets.tableviews import SardesTableWidget
from sardes.tables.models import StandardSardesTableModel
from sardes.tables.delegates import (
    ObsWellIdEditDelegate, BoolEditDelegate, NotEditableDelegate,
    TextEditDelegate, DateTimeDelegate, NumEditDelegate)


class RepereTableModel(StandardSardesTableModel):
    """
    A table model to display the repere data related to the observation
    wells of the monitoring network.
    """
    __tablename__ = 'table_repere'
    __tabletitle__ = _('Repere')
    __tablecolumns__ = [
        SardesTableColumn(
            'sampling_feature_uuid', _('Well ID'), 'str', notnull=True,
            delegate=ObsWellIdEditDelegate),
        SardesTableColumn(
            'top_casing_alt', _('Top Casing Alt. (m)'), 'float64',
            notnull=True,
            delegate=NumEditDelegate,
            delegate_options={
                'decimals': 3, 'minimum': -99999, 'maximum': 99999}),
        SardesTableColumn(
            'casing_length', _('Length Casing (m)'), 'float64', notnull=True,
            delegate=NumEditDelegate,
            delegate_options={
                'decimals': 3, 'minimum': -99999, 'maximum': 99999}),
        SardesTableColumn(
            'start_date', _('Date From'), 'datetime64[ns]', notnull=True,
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd hh:mm"}),
        SardesTableColumn(
            'end_date', _('Date To'), 'datetime64[ns]',
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd hh:mm"}),
        SardesTableColumn(
            'is_alt_geodesic', _('Geodesic'), 'boolean', notnull=True,
            delegate=BoolEditDelegate),
        SardesTableColumn(
            'repere_note', _('Notes'), 'str',
            delegate=TextEditDelegate)
        ]

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
        table_model = RepereTableModel()
        super().__init__(table_model, *args, **kargs)
