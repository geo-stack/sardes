# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Third party imports
import pandas as pd
from qtpy.QtWidgets import QComboBox

# ---- Local imports
from sardes.config.locale import _
from sardes.widgets.tableviews import (
    SardesItemDelegate, SardesTableModel, SardesTableWidget,
    NotEditableDelegate, DateTimeDelegate, NumEditDelegate)


class ObsWellIdEditDelegate(SardesItemDelegate):
    """
    A delegate to select an obsercation well from the list of existing well
    in the database.
    """

    def create_editor(self, parent):
        editor = QComboBox(parent)

        # Populate the combobox with the existing observation wells.
        obs_well_data = (self.model().libraries['observation_wells_data']
                         .sort_values('obs_well_id', axis=0, ascending=True))
        for index in obs_well_data.index:
            editor.addItem(obs_well_data.loc[index, 'obs_well_id'],
                           userData=index)
        return editor


class ManualMeasurementsTableModel(SardesTableModel):
    """
    A table model to display the list of manual groundwater level measurements
    made in the observation wells of the monitoring network.
    """
    # The label that will be used to reference this table in the GUI.
    TABLE_TITLE = _('Manual Measurements')

    # An id that will be used to reference this table in the code and
    # in the user configurations.
    TABLE_ID = 'table_manual_measurements'

    # A list of tuple that maps the keys of the columns dataframe with their
    # corresponding human readable label to use in the GUI.
    __data_columns_mapper__ = [
        ('sampling_feature_uuid', _('Well ID')),
        ('datetime', _('Date/Time')),
        ('manual_measurement', _('Water Level')),
        ]

    # Provide the name of the data and of the required libraries that
    # this table need to fetch from the database.
    TABLE_DATA_NAME = 'manual_measurements'
    REQ_LIB_NAMES = ['observation_wells_data']

    # ---- Delegates
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
        elif column == 'manual_measurement':
            return NumEditDelegate(view, decimals=3, bottom=-99999, top=99999)
        else:
            return NotEditableDelegate(view)

    # ---- Visual Data
    def logical_to_visual_data(self, visual_dataf):
        """
        Transform logical data to visual data.
        """
        obs_wells_data = self.libraries['observation_wells_data']
        visual_dataf['sampling_feature_uuid'] = (
            visual_dataf['sampling_feature_uuid']
            .replace(self._obs_well_data['obs_well_id'].to_dict())
            )
        visual_dataf['datetime'] = (visual_dataf['datetime']
                                    .dt.strftime('%Y-%m-%d %H:%M'))
        return visual_dataf

    # ---- Data edits
    def save_data_edits(self):
        """
        Save all data edits to the database.
        """
        pass


class ManualMeasurementsTableWidget(SardesTableWidget):
    def __init__(self, db_connection_manager, parent=None):
        table_model = ManualMeasurementsTableModel(db_connection_manager)
        super().__init__(table_model, parent)
