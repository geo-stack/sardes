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
        self._tseries_data_tables = {}

    # ---- Public methods implementation
    def current_table(self):
        """
        Return the currently visible table of this plugin.
        """
        return self.tabwidget.currentWidget()

    def count(self):
        """
        Return the number of tables installed this plugin.
        """
        return len(self._tseries_data_tables)

    @classmethod
    def get_plugin_title(cls):
        """Return widget title"""
        return _('Readings')

    def create_pane_widget(self):
        """
        Create and return the pane widget to use in this
        plugin's dockwidget.
        """
        self.tabwidget = QTabWidget(self.main)
        self.tabwidget.setTabPosition(self.tabwidget.North)
        self.tabwidget.setIconSize(QSize(18, 18))
        self.tabwidget.setTabsClosable(True)
        self.tabwidget.tabCloseRequested.connect(self._close_readings_table_at)
        return self.tabwidget

    def close_plugin(self):
        """
        Extend Sardes plugin method to save user inputs in the
        configuration file.
        """
        super().close_plugin()

        # Close all opened timeseries data table.
        self._close_all_readings_tables()

    def register_plugin(self):
        """
        Extend base class method to do some connection with the database
        manager to update the tables' data.
        """
        super().register_plugin()
        self.main.db_connection_manager.sig_tseries_data_changed.connect(
            self.update_timeseries_data)
        self.main.db_connection_manager.sig_database_disconnected.connect(
            self._close_all_readings_tables)

    # ---- Private methods
    def _update_tab_names(self):
        """
        Append a '*' symbol at the end of a tab name when its corresponding
        table have unsaved edits.
        """
        for index in range(self.count()):
            table = self.tabwidget.widget(index)
            tab_text = table.get_table_title()
            if table.tableview.model().has_unsaved_data_edits():
                tab_text += '*'
            self.tabwidget.setTabText(index, tab_text)

    def _update_current_table(self, *args, **kargs):
        """Update the current table data and state."""
        return
        if self.current_table().isVisible():
            self.current_table().setEnabled(
                self.main.db_connection_manager.is_connected())
            self.current_table().update_model_data()

    @Slot(object)
    def _handle_data_table_destroyed(self, obs_well_uuid):
        """
        Handle when a timeseries data table is destroyed.
        """
        del self._tseries_data_tables[obs_well_uuid]

    # ---- Timeseries data tables
    def _close_readings_table_at(self, index):
        """
        Close the readings table at the given tabwidget index.
        """
        table_widget = self.tabwidget.widget(index)
        self.tabwidget.removeTab(index)
        table_widget.close()

    def _close_all_readings_tables(self):
        """Close all opened timeseries data table."""
        for index in reversed(range(self.count())):
            self._close_readings_table_at(index)

    def view_timeseries_data(self, obs_well_uuid):
        """
        Create and show a table to visualize the timeseries data contained
        in tseries_groups.
        """
        self.switch_to_plugin()
        if obs_well_uuid not in self._tseries_data_tables:
            self.main.db_connection_manager.get(
                'observation_wells_data',
                obs_well_uuid,
                callback=lambda obs_wells_data: self._create_timeseries_data(
                    obs_wells_data.loc[obs_well_uuid]))
        else:
            data_table = self._tseries_data_tables[obs_well_uuid]
            self.tabwidget.setCurrentWidget(data_table)
            data_table.tableview.setFocus()

    def _create_timeseries_data(self, obs_well_data):
        """
        Create a new timeseries data for the observation well related to the
        given data.
        """
        obs_well_uuid = obs_well_data.name
        obs_well_id = obs_well_data['obs_well_id']

        # Setup a new table model and widget.
        table_model = DataTableModel(obs_well_uuid, table_title=obs_well_id,
                                     table_id=obs_well_uuid)
        table_model.set_database_connection_manager(
            self.main.db_connection_manager)

        table_widget = SardesTableWidget(
            table_model, parent=self.main, multi_columns_sort=True,
            sections_movable=False, sections_hidable=False,
            disabled_actions=['new_row'])
        table_widget.setAttribute(Qt.WA_DeleteOnClose)
        table_widget.destroyed.connect(
            lambda _, obs_well_uuid=obs_well_uuid:
                self._handle_data_table_destroyed(obs_well_uuid))

        # Set the title of the window.
        table_widget.setWindowTitle(_("Observation well {} ({})").format(
            obs_well_id, obs_well_data['municipality']))

        # Columns width and minimum window size.
        horizontal_header = table_widget.tableview.horizontalHeader()
        horizontal_header.setDefaultSectionSize(125)

        self._tseries_data_tables[obs_well_uuid] = table_widget
        self.tabwidget.addTab(
            table_widget, get_icon('table'), obs_well_data['obs_well_id'])
        table_widget.tableview.sig_data_edited.connect(self._update_tab_names)
        table_widget.tableview.sig_data_updated.connect(self._update_tab_names)

        self.view_timeseries_data(obs_well_uuid)
        table_model.update_data()

    def update_timeseries_data(self, obs_well_ids):
        """
        Update the timeseries data table according to the provided list
        of well observation wells.
        """
        for obs_well_id in obs_well_ids:
            if obs_well_id in self._tseries_data_tables:
                self._tseries_data_tables[obs_well_id].model().update_data()
