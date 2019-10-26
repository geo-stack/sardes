# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Third party imports
from qtpy.QtWidgets import QComboBox

# ---- Local imports
from sardes.api.tablemodels import SardesTableModel
from sardes.config.locale import _
from sardes.widgets.tableviews import (
    SardesItemDelegate, SardesTableWidget, StringEditDelegate,
    BoolEditDelegate, NotEditableDelegate, TextEditDelegate, DateEditDelegate)


class SondeModelEditDelegate(SardesItemDelegate):
    """
    A delegate to select the brand of a sonde from a predefined list.
    """

    def create_editor(self, parent):
        editor = QComboBox(parent)

        # Populate the combobox with the available brand in the library.
        sonde_models_lib = self.model().libraries['sonde_models_lib']
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

    # Provide the name of the data and of the required libraries that
    # this table need to fetch from the database.
    TABLE_DATA_NAME = 'sondes_data'
    REQ_LIB_NAMES = ['sonde_models_lib']

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

    # ---- Visual Data
    def logical_to_visual_data(self, visual_dataf):
        """
        Transform logical data to visual data.
        """
        sonde_models_lib = self.libraries['sonde_models_lib']
        visual_dataf['sonde_model_id'] = (
            visual_dataf['sonde_model_id']
            .replace(sonde_models_lib['sonde_brand_model'].to_dict())
            )
        return visual_dataf


class SondesInventoryTableWidget(SardesTableWidget):
    def __init__(self, db_connection_manager, parent=None):
        table_model = SondesInventoryTableModel(db_connection_manager)
        super().__init__(table_model, parent)
