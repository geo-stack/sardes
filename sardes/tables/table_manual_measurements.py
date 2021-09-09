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
        SardesTableColumn(
            'sampling_feature_uuid', _('Well ID'), 'str',
            notnull=True, unique=True,
            delegate=ObsWellIdEditDelegate),
        SardesTableColumn(
            'datetime', _('Date/Time'), 'datetime64[ns]', notnull=True,
            unique=True, unique_subset=['sampling_feature_uuid'],
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd hh:mm:ss"}),
        SardesTableColumn(
            'value', _('Water Level'), 'float64', notnull=True,
            delegate=NumEditDelegate,
            delegate_options={
                'decimals': 3, 'minimum': -99999, 'maximum': 99999}),
        SardesTableColumn(
            'notes', _('Notes'), 'str',
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

        return visual_dataf


class ManualMeasurementsTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = ManualMeasurementsTableModel()
        super().__init__(table_model, *args, **kargs)

        # Add the tool to import data from the clipboard.
        self.install_tool(
            ImportFromClipboardTool(self), after='copy_to_clipboard')
