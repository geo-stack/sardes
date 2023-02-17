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
from sardes.tables.delegates import (
    ObsWellIdEditDelegate, TextEditDelegate, DateTimeDelegate, NumEditDelegate)
from sardes.widgets.tableviews import (
    SardesTableWidget, ImportFromClipboardTool)


class ManualMeasurementsTableModel(StandardSardesTableModel):
    """
    A table model to display the list of manual groundwater level measurements
    made in the observation wells of the monitoring network.
    """
    __tablename__ = 'table_manual_measurements'
    __tabletitle__ = _('Manual Measurements')
    __tablecolumns__ = [
        sardes_table_column_factory(
            'manual_measurements', 'sampling_feature_uuid', _('Well ID'),
            delegate=ObsWellIdEditDelegate),
        sardes_table_column_factory(
            'manual_measurements', 'datetime', _('Date'),
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd hh:mm:ss"}),
        sardes_table_column_factory(
            'manual_measurements', 'value', _('Water Level'),
            delegate=NumEditDelegate,
            delegate_options={
                'decimals': 3, 'minimum': -99999, 'maximum': 99999}),
        sardes_table_column_factory(
            'manual_measurements', 'notes', _('Notes'),
            delegate=TextEditDelegate)
        ]

    __dataname__ = 'manual_measurements'
    __libnames__ = ['observation_wells_data']


class ManualMeasurementsTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = ManualMeasurementsTableModel()
        super().__init__(table_model, *args, **kargs)

        # Add the tool to import data from the clipboard.
        self.install_tool(
            ImportFromClipboardTool(self), after='copy_to_clipboard')
