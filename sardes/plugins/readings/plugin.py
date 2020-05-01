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
from sardes.utils.qthelpers import create_toolbutton
from sardes.config.gui import get_iconsize
from sardes.api.tablemodels import SardesTableModel
from sardes.api.timeseries import DataType, merge_timeseries_groups
from sardes.config.main import CONF
from sardes.widgets.timeseries import TimeSeriesPlotViewer
from sardes.widgets.tableviews import (
    SardesTableWidget, StringEditDelegate, BoolEditDelegate,
    NumEditDelegate, NotEditableDelegate, TextEditDelegate,
    SardesStackedTableWidget)


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
        self.tabwidget = SardesStackedTableWidget(
            self.main, tabs_closable=True, tabs_movable=True)
        return self.tabwidget

    def close_plugin(self):
        """
        Extend Sardes plugin method to save user inputs in the
        configuration file.
        """
        super().close_plugin()

        # Close all opened timeseries data table.
        self.tabwidget.close_all_tables()

    def register_plugin(self):
        """
        Extend base class method to do some connection with the database
        manager to update the tables' data.
        """
        super().register_plugin()
        self.main.db_connection_manager.sig_tseries_data_changed.connect(
            self._update_readings_tables)
        self.main.db_connection_manager.sig_database_disconnected.connect(
            self.tabwidget.close_all_tables)

    def on_docked(self):
        """
        Implement SardesPlugin abstract method.
        """
        # Hide stacked table widget statusbar.
        self.tabwidget.statusBar().hide()

        # Register each table to main.
        for table in self._tseries_data_tables.values():
            self.main.register_table(table.tableview)

    def on_undocked(self):
        """
        Implement SardesPlugin abstract method.
        """
        # Show stacked table widget statusbar.
        self.tabwidget.statusBar().show()

        # Un-register each table from main.
        for table in self._tseries_data_tables.values():
            self.main.unregister_table(table.tableview)

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
        self.main.unregister_table(
            self._tseries_data_tables[obs_well_uuid].tableview)
        del self._tseries_data_tables[obs_well_uuid]

    # ---- Readings tables
    def view_timeseries_data(self, obs_well_uuid):
        """
        Create and show a table to visualize the timeseries data contained
        in tseries_groups.
        """
        self.switch_to_plugin()
        if obs_well_uuid not in self._tseries_data_tables:
            self.main.db_connection_manager.get(
                'observation_wells_data',
                callback=lambda obs_wells_data: self._create_readings_table(
                    obs_wells_data.loc[obs_well_uuid])
                )
        else:
            data_table = self._tseries_data_tables[obs_well_uuid]
            self.tabwidget.setCurrentWidget(data_table)
            data_table.tableview.setFocus()

    def _create_readings_table(self, obs_well_data):
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

        # Add show plot button.
        table_widget.add_toolbar_separator()
        show_plot_btn = create_toolbutton(
            table_widget,
            icon='show_plot',
            text=_("Plot data"),
            tip=_('Show the data of the timeseries acquired in the currently '
                  'selected observation well in an interactive '
                  'plot viewer.'),
            triggered=lambda _: self._request_plot_readings(obs_well_data),
            iconsize=get_iconsize()
            )
        table_widget.add_toolbar_widget(show_plot_btn)

        # Set the title of the window.
        table_widget.setWindowTitle(_("Observation well {} ({})").format(
            obs_well_id, obs_well_data['municipality']))

        # Columns width and minimum window size.
        horizontal_header = table_widget.tableview.horizontalHeader()
        horizontal_header.setDefaultSectionSize(125)

        self._tseries_data_tables[obs_well_uuid] = table_widget
        self.tabwidget.add_table(
            table_widget, obs_well_data['obs_well_id'], switch_to_table=True)
        if self.dockwindow.is_docked():
            self.main.register_table(table_widget.tableview)

        table_model.update_data()

    def _update_readings_tables(self, obs_well_ids):
        """
        Update the readings tables according to the provided list of
        observation well ids.
        """
        for obs_well_id in obs_well_ids:
            if obs_well_id in self._tseries_data_tables:
                self._tseries_data_tables[obs_well_id].model().update_data()

    # ---- Plots
    def _request_plot_readings(self, obs_well_data):
        """
        Handle when a request has been made to show the data of the currently
        selected well in a plot.
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.main.db_connection_manager.get_timeseries_for_obs_well(
            obs_well_data.name,
            [DataType.WaterLevel, DataType.WaterTemp, DataType.WaterEC],
            callback=lambda tseries_groups: self.plot_readings(
                tseries_groups, obs_well_data))

    def plot_readings(self, tseries_groups, obs_well_data):
        """
        Create and show a timeseries plot viewer to visualize interactively
        the timeseries data contained in tseries_groups.
        """
        viewer = TimeSeriesPlotViewer(self.main)

        # Set the title of the window.
        window_title = '{}'.format(obs_well_data['obs_well_id'])
        if obs_well_data['common_name']:
            window_title += ' - {}'.format(obs_well_data['common_name'])
        if obs_well_data['municipality']:
            window_title += ' ({})'.format(obs_well_data['municipality'])
        viewer.setWindowTitle(window_title)

        # Setup the data for the timeseries plot viewer.
        # where = 'left'
        for tseries_group in tseries_groups[:2]:
            # Create a new axe to hold the timeseries for the monitored
            # property related to this group of timeseries.
            viewer.create_axe(tseries_group)
        QApplication.restoreOverrideCursor()
        viewer.show()
        viewer.raise_()
