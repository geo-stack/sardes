# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Local imports
from sardes.api.tablemodels import SardesTableModel
from sardes.config.locale import _
from sardes.widgets.tableviews import (
    SardesTableWidget, TextEditDelegate, NotEditableDelegate, DateTimeDelegate,
    NumEditDelegate)
from sardes.plugins.tables.tables.delegates import ObsWellIdEditDelegate


class ManualMeasurementsTableModel(SardesTableModel):
    """
    A table model to display the list of manual groundwater level measurements
    made in the observation wells of the monitoring network.
    """

    def create_delegate_for_column(self, view, column):
        """
        Create the item delegate that the view need to use when editing the
        data of this model for the specified column. If None is returned,
        the items of the column will not be editable.
        """
        if column == 'sampling_feature_uuid':
            return ObsWellIdEditDelegate(view)
        elif column == 'datetime':
            return DateTimeDelegate(view, display_format="yyyy-MM-dd hh:mm")
        elif column == 'value':
            return NumEditDelegate(view, decimals=3, bottom=-99999, top=99999)
        elif column == 'notes':
            return TextEditDelegate(view)
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
        visual_dataf['datetime'] = (visual_dataf['datetime']
                                    .dt.strftime('%Y-%m-%d %H:%M'))
        return visual_dataf


class ManualMeasurementsTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = ManualMeasurementsTableModel(
            table_title=_('Manual Measurements'),
            table_id='table_manual_measurements',
            data_columns_mapper=[
                ('sampling_feature_uuid', _('Well ID')),
                ('datetime', _('Date/Time')),
                ('value', _('Water Level')),
                ('notes', _('Notes'))]
            )
        super().__init__(table_model, *args, **kargs)
