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
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QComboBox

# ---- Local imports
from sardes.config.locale import _
from sardes.widgets.tableviews import (
    SardesItemDelegate, SardesTableModel, SardesTableWidget,
    StringEditDelegate, BoolEditDelegate, NotEditableDelegate,
    TextEditDelegate, DateEditDelegate)


class SondeModelEditDelegate(SardesItemDelegate):
    """
    A delegate to select the brand of a sonde from a predefined list.
    """

    def create_editor(self, parent):
        editor = QComboBox(parent)

        # Populate the combobox with the available brand in the library.
        sonde_models_lib = self.model_view.source_model._sonde_models_lib
        for index in sonde_models_lib.index:
            editor.addItem(sonde_models_lib.loc[index, 'sonde_brand_model'],
                           userData=index)
        return editor


class SondesInventoryTableModel(SardesTableModel):
    """
    A table model to display the list of level and baro loggers that are
    used in the monitoring network.
    """
    # The label that will be used to reference this table in the GUI.
    TABLE_TITLE = _('Sondes Inventory')

    # An id that will be used to reference this table in the code and
    # in the user configurations.
    TABLE_ID = 'table_sondes_inventory'

    # A list of tuple that maps the keys of the columns dataframe with their
    # corresponding human readable label to use in the GUI.
    __data_columns_mapper__ = [
        ('sonde_model_id', _('Model')),
        ('sonde_serial_no', _('Serial Number')),
        ('date_reception', _('Date Reception')),
        ('date_withdrawal', _('Date Withdrawal')),
        ('in_repair', _('In Repair')),
        ('out_of_order', _('Out of order')),
        ('lost', _('Lost')),
        ('off_network', _('Off Network')),
        ('sonde_notes', _('Notes')),
        ]

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self._sonde_models_lib = None

    def fetch_model_data(self, *args, **kargs):
        """
        Fetch the observation well data for this table model.
        """
        # Note we need to fetch the sonde models library before we fetch
        # the sonde data.
        self.db_connection_manager.get_sonde_models_lib(
            callback=self.set_sonde_models_lib, postpone_exec=True)
        self.db_connection_manager.get_sondes_data(
            callback=self.set_model_data, postpone_exec=True)
        self.db_connection_manager.run_tasks()

    # ---- Sonde models library.
    def set_sonde_models_lib(self, sonde_models_lib):
        """
        Set the sonde model library that this model is going
        to use for its 'sonde_brand' and 'sonde_model' item delegates.
        """
        self._sonde_models_lib = sonde_models_lib

    def get_sonde_model_at(self, model_index):
        """
        Return a human readable string containing the brand and the
        model of the sonde corresponding to the specified model_index.
        """
        sonde_model_id = self.get_value_at(model_index)
        if pd.isna(sonde_model_id) or sonde_model_id is None:
            return ''
        else:
            return (self._sonde_models_lib
                    .loc[sonde_model_id, 'sonde_brand_model'])

    # ---- Delegates
    def create_delegate_for_column(self, view, column):
        """
        Create the item delegate that the view need to use when editing the
        data of this model for the specified column. If None is returned,
        the items of the column will not be editable.
        """
        if column in ['en_reparation', 'out_of_order', 'in_repair',
                      'lost', 'off_network']:
            return BoolEditDelegate(view, is_required=True)
        elif column in ['date_reception', 'date_withdrawal']:
            return DateEditDelegate(view)
        elif column == 'sonde_notes':
            return TextEditDelegate(view)
        elif column == 'sonde_serial_no':
            return StringEditDelegate(view)
        elif column == 'sonde_model_id':
            return SondeModelEditDelegate(view, is_required=True)
        else:
            return NotEditableDelegate(view)

    # ---- Data edits
    def save_data_edits(self):
        """
        Save all data edits to the database.
        """
        for edits in self._dataf_edits:
            for edit in edits:
                if edit.type() == self.ValueChanged:
                    self.db_connection_manager.save_sonde_data(
                        edit.index, edit.column, edit.edited_value,
                        postpone_exec=True)
        self.db_connection_manager.run_tasks()

    # ---- Data display
    def data(self, index, role=Qt.DisplayRole):
        """
        Override base class method to display a human readable string of the
        brand and model of the sondes instead of a database ID.
        """
        if self.columns[index.column()] == 'sonde_model_id':
            if role in [Qt.DisplayRole, Qt.ToolTipRole]:
                return self.get_sonde_model_at(index)
        return super().data(index, role)


class SondesInventoryTableWidget(SardesTableWidget):
    def __init__(self, db_connection_manager, parent=None):
        table_model = SondesInventoryTableModel(db_connection_manager)
        super().__init__(table_model, parent)
