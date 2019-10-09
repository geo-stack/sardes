# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QFileDialog
import pandas as pd


# ---- Local imports
from sardes.widgets.timeseries import TimeSeriesPlotViewer
from sardes.config.gui import get_iconsize
from sardes.config.locale import _
from sardes.tools.dataio import export_data_to_file
from sardes.utils.qthelpers import create_toolbutton
from sardes.widgets.tableviews import (
    SardesTableModel, SardesTableWidget, StringEditDelegate, BoolEditDelegate,
    NumEditDelegate, NotEditableDelegate, TextEditDelegate)


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
        ('sonde_id', _('Sonde ID')),
        ('date_reception', _('Date Reception')),
        ('date_withdrawal', _('Date Withdrawal')),
        ('en_reparation', _('Date Withdrawal')),
        ('out_of_order', _('Out of order')),
        ('in_repair', _('In Repair')),
        ('lost', _('Lost')),
        ('off_network', _('Off Network')),
        ('sonde_notes', _('Remarque')),
        ]

    def fetch_model_data(self, *args, **kargs):
        """
        Fetch the observation well data for this table model.
        """
        columns = list(self._data_columns_mapper.keys())
        data = ['123123', 'qwer', '06-08-2019', '05-03-04',
                True, True, False, False, True, 'Some notes']
        # self.set_model_data(pd.DataFrame(data, columns=columns))
        self.set_model_data(pd.DataFrame())

        # self.db_connection_manager.get_observation_wells_data(
        #     callback=self.set_model_data)

    # ---- Delegates
    def create_delegate_for_column(self, view, column):
        """
        Create the item delegate that the view need to use when editing the
        data of this model for the specified column. If None is returned,
        the items of the column will not be editable.
        """
        if column in ['en_reparation', 'out_of_order', 'in_repair',
                      'lost', 'off_network']:
            return BoolEditDelegate(view)
        else:
            return NotEditableDelegate(self)

    # ---- Data edits
    def save_data_edits(self):
        """
        Save all data edits to the database.
        """
        pass
        # for edit in self._dataf_edits:
        #     if edit.type() == self.ValueChanged:
        #         self.db_connection_manager.save_observation_well_data(
        #             edit.dataf_index, edit.dataf_column,
        #             edit.edited_value, postpone_exec=True)
        # self.db_connection_manager.run_tasks()


class SondesInventoryTableWidget(SardesTableWidget):
    def __init__(self, db_connection_manager, parent=None):
        table_model = SondesInventoryTableModel(db_connection_manager)
        super().__init__(table_model, parent)
