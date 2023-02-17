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
from sardes.api.tablemodels import (
    SardesTableColumn, sardes_table_column_factory)
from sardes.config.locale import _
from sardes.widgets.tableviews import SardesTableWidget
from sardes.tables.models import StandardSardesTableModel
from sardes.tables.delegates import (
    ObsWellIdEditDelegate, BoolEditDelegate, TextEditDelegate,
    DateTimeDelegate, NumEditDelegate)


class RepereTableModel(StandardSardesTableModel):
    """
    A table model to display the repere data related to the observation
    wells of the monitoring network.
    """
    __tablename__ = 'table_repere'
    __tabletitle__ = _('Repere')
    __tablecolumns__ = [
        sardes_table_column_factory(
            'repere_data', 'sampling_feature_uuid', _('Well ID'),
            delegate=ObsWellIdEditDelegate),
        sardes_table_column_factory(
            'repere_data', 'top_casing_alt', _('Top Casing Alt. (m)'),
            delegate=NumEditDelegate,
            delegate_options={
                'decimals': 3, 'minimum': -99999, 'maximum': 99999}),
        sardes_table_column_factory(
            'repere_data', 'casing_length', _('Length Casing (m)'),
            delegate=NumEditDelegate,
            delegate_options={
                'decimals': 3, 'minimum': -99999, 'maximum': 99999}),
        SardesTableColumn(
            'ground_altitude', _('Ground Alt. (m)'), 'float64', editable=False,
            delegate=NumEditDelegate,
            delegate_options={
                'decimals': 3, 'minimum': -99999, 'maximum': 99999}),
        sardes_table_column_factory(
            'repere_data', 'start_date', _('Date From'),
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd hh:mm"}),
        sardes_table_column_factory(
            'repere_data', 'end_date', _('Date To'),
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd hh:mm"}),
        sardes_table_column_factory(
            'repere_data', 'is_alt_geodesic', _('Geodesic'),
            delegate=BoolEditDelegate),
        sardes_table_column_factory(
            'repere_data', 'repere_note', _('Notes'),
            delegate=TextEditDelegate)
        ]

    __dataname__ = 'repere_data'
    __libnames__ = ['observation_wells_data']

    # ---- Visual Data
    def logical_to_visual_data(self, visual_dataf):
        """
        Transform logical data to visual data.
        """
        visual_dataf['ground_altitude'] = (
            visual_dataf['top_casing_alt'] - visual_dataf['casing_length'])
        return super().logical_to_visual_data(visual_dataf)


class RepereTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = RepereTableModel()
        super().__init__(table_model, *args, **kargs)
