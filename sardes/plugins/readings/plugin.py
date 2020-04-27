# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Local imports
from sardes.api.plugins import SardesPlugin
from sardes.config.icons import get_icon
from sardes.config.locale import _
from sardes.plugins.tables.tables import (
    ObsWellsTableWidget, RepereTableWidget, SondesInventoryTableWidget,
    ManualMeasurementsTableWidget, SondeInstallationsTableWidget)

# ---- Third party imports
import pandas as pd
from qtpy.QtCore import Qt, QSize, Slot
from qtpy.QtWidgets import (QApplication, QFileDialog, QTabWidget,
                            QLabel, QFrame, QGridLayout, QWidget,
                            QPushButton, QToolButton, QStyle)

# ---- Local imports
from sardes.api.tablemodels import SardesTableModel
from sardes.api.timeseries import DataType, merge_timeseries_groups
from sardes.config.main import CONF
from sardes.widgets.tableviews import (
    SardesTableWidget, StringEditDelegate, BoolEditDelegate,
    NumEditDelegate, NotEditableDelegate, TextEditDelegate)


"""Readings plugin"""


class DataTableModel(SardesTableModel):
    def __init__(self, obs_well_uuid, *args, **kargs):
        super().__init__(*args, **kargs)
        self._obs_well_uuid = obs_well_uuid

    def create_delegate_for_column(self, view, column):
        if isinstance(column, DataType):
            return NumEditDelegate(
                view, decimals=6, bottom=-99999, top=99999)
        else:
            return NotEditableDelegate(view)

    # ---- Database connection
    def update_data(self):
        """
        Update this model's data and library.
        """
        self.sig_data_about_to_be_updated.emit()

        # Get the timeseries data for that observation well.
        self.db_connection_manager.get_timeseries_for_obs_well(
            self._obs_well_uuid,
            [DataType.WaterLevel, DataType.WaterTemp, DataType.WaterEC],
            self.set_model_tseries_groups)

    def set_model_tseries_groups(self, tseries_groups):
        """
        Format the data contained in the list of timeseries group and
        set the content of this table model data.
        """
        dataf = merge_timeseries_groups(tseries_groups)
        dataf_columns_mapper = [('datetime', _('Datetime')),
                                ('sonde_id', _('Sonde Serial Number'))]
        dataf_columns_mapper.extend([(dtype, dtype.label) for dtype in
                                     DataType if dtype in dataf.columns])
        dataf_columns_mapper.append(('obs_id', _('Observation ID')))
        self.set_model_data(dataf, dataf_columns_mapper)
        self.sig_data_updated.emit()

    def save_data_edits(self):
        """
        Save all data edits to the database.
        """
        self.sig_data_about_to_be_saved.emit()

        tseries_edits = pd.DataFrame(
            [], columns=['datetime', 'obs_id', 'data_type', 'value'])
        tseries_edits.set_index(
            'datetime', inplace=True, drop=True)
        tseries_edits.set_index(
            'obs_id', inplace=True, drop=True, append=True)
        tseries_edits.set_index(
            'data_type', inplace=True, drop=True, append=True)

        tseries_dels = pd.DataFrame(
            [], columns=['obs_id', 'datetime', 'data_type'])

        for edit in self._datat.edits():
            if edit.type() == SardesTableModel.ValueChanged:
                row_data = self._datat.get(edit.row)
                date_time = row_data['datetime']
                obs_id = row_data['obs_id']
                indexes = (date_time, obs_id, edit.column)
                tseries_edits.loc[indexes, 'value'] = edit.edited_value
            elif edit.type() == SardesTableModel.RowDeleted:
                delrows_data = self._datat.get(edit.row)
                data_types = [dtype for dtype in DataType if
                              dtype in delrows_data.keys()]
                for data_type in data_types:
                    delrows_data_type = (
                        delrows_data.copy()[['obs_id', 'datetime']])
                    delrows_data_type['data_type'] = data_type
                    tseries_dels = tseries_dels.append(
                        delrows_data_type, ignore_index=True)
        tseries_dels.drop_duplicates()
        self.db_connection_manager.delete_timeseries_data(
            tseries_dels, self._obs_well_uuid,
            callback=None, postpone_exec=True)
        self.db_connection_manager.save_timeseries_data_edits(
            tseries_edits, self._obs_well_uuid,
            callback=self._handle_data_edits_saved, postpone_exec=True)
        self.db_connection_manager.run_tasks()

    def _handle_data_edits_saved(self):
        """
        Handle when data edits were all saved in the database.
        """
        self.sig_data_saved.emit()


class Readings(SardesPlugin):

    CONF_SECTION = 'readings'

    def __init__(self, parent):
        super().__init__(parent)
