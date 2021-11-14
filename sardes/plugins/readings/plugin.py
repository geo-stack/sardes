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
from sardes.config.locale import _

# ---- Third party imports
import pandas as pd
from qtpy.QtCore import Qt, Slot

# ---- Local imports
from sardes.api.tablemodels import SardesTableColumn
from sardes.api.timeseries import DataType
from sardes.config.icons import get_icon
from sardes.config.gui import get_iconsize
from sardes.tables.delegates import NumEditDelegate, NotEditableDelegate
from sardes.api.tablemodels import SardesTableModel
from sardes.utils.qthelpers import create_toolbutton
from sardes.utils.data_operations import format_reading_data
from sardes.widgets.timeseries import TimeSeriesPlotViewer
from sardes.widgets.tableviews import (
    SardesTableWidget, SardesStackedTableWidget)
from sardes.tools import (
    SaveReadingsToExcelTool, HydrographTool, SatisticalHydrographTool)
from sardes.database.accessors.accessor_helpers import (
    init_tseries_edits, init_tseries_dels)


"""Readings plugin"""


class ReadingsTableModel(SardesTableModel):

    def __init__(self, obs_well_data, obs_well_id, obs_well_uuid):
        self.__tablecolumns__ = []
        self.__tabletitle__ = obs_well_id
        self.__tablename__ = obs_well_uuid
        self._is_saving_edits = False
        self.dbconnmanager = None
        super().__init__()

        self._obs_well_data = obs_well_data
        self._obs_well_uuid = obs_well_data.name
        self._repere_data = pd.Series([], dtype=object)
        self._manual_measurements = pd.DataFrame(
            [], columns=['datetime', 'value'])

    def set_database_connection_manager(self, dbconnmanager):
        """Set the namespace for Sardes database connection manager."""
        self.dbconnmanager = dbconnmanager

    # ---- Data
    def set_obs_well_data(self, obs_well_data):
        self._obs_well_data = obs_well_data.loc[self._obs_well_uuid]
        self.set_title(str(self._obs_well_data['obs_well_id']))

    def manual_measurements(self):
        return self._manual_measurements

    def set_manual_measurements(self, manual_measurements):
        self._manual_measurements = (
            manual_measurements
            [manual_measurements['sampling_feature_uuid'] ==
             self._obs_well_uuid]
            [['datetime', 'value']]
            .copy())

    def set_repere_data(self, repere_data):
        repere_data = (
            repere_data
            [repere_data['sampling_feature_uuid'] == self._obs_well_uuid]
            .copy())
        if not repere_data.empty:
            self._repere_data = (
                repere_data
                .sort_values(by=['end_date'], ascending=[True]))
        else:
            self._repere_data = pd.Series([], dtype=object)

    def set_model_data(self, dataf):
        """
        Format the data contained in the list of timeseries group and
        set the content of this table model data.
        """
        self.sig_data_about_to_be_updated.emit()
        columns = [
            SardesTableColumn(
                'datetime', _('Datetime'), 'datetime64[ns]',
                delegate=NotEditableDelegate, editable=False),
            SardesTableColumn(
                'sonde_id', _('Sonde Serial Number'), 'str',
                delegate=NotEditableDelegate, editable=False)
            ]
        for dtype in DataType:
            if dtype in dataf.columns:
                columns.append(SardesTableColumn(
                    dtype, dtype.label, 'float64',
                    delegate=NumEditDelegate,
                    delegate_options={'decimals': 6,
                                      'minimum': -99999,
                                      'maximum': 99999}
                    ))
        columns.extend([
            SardesTableColumn(
                'install_depth', _('Depth'), 'float64',
                delegate=NotEditableDelegate, editable=False),
            SardesTableColumn(
                'obs_id', _('Observation ID'), 'str',
                delegate=NotEditableDelegate, editable=False)
            ])
        super().set_model_data(dataf, columns)
        self.sig_data_updated.emit()

    # ---- SardesTableModel API
    def check_data_edits(self, callback):
        """
        Check that there is no issues with the data edits of this model.
        """
        callback(error=None)

    def save_data_edits(self):
        """
        Save all data edits to the database.
        """
        self._is_saving_edits = True
        self.sig_data_about_to_be_saved.emit()

        tseries_edits = init_tseries_edits()
        tseries_dels = init_tseries_dels()
        for edit in self._datat.edits():
            if edit.type() == self.EditValue:
                if self._datat.is_data_deleted_at(edit.row):
                    continue
                row_data = self._datat.get(edit.row)
                date_time = row_data['datetime']
                obs_id = row_data['obs_id']
                indexes = (date_time, obs_id, edit.column)
                tseries_edits.loc[indexes, 'value'] = edit.edited_value
            elif edit.type() == self.DeleteRows:
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

        self.dbconnmanager.add_task(
            'save_readings_edits',
            callback=self._handle_data_edits_saved,
            station_id=self._obs_well_uuid,
            tseries_edits=tseries_edits,
            tseries_dels=tseries_dels,
            )
        self.dbconnmanager.run_tasks()

    def _handle_data_edits_saved(self, dataf):
        """
        Handle when data edits were all saved in the database.
        """
        self.sig_data_saved.emit()
        self.set_model_data(dataf)
        self.dbconnmanager.sig_tseries_data_changed.emit([self._obs_well_uuid])
        self._is_saving_edits = False

    def confirm_before_saving_edits(self):
        """
        Return wheter we should ask confirmation to the user before saving
        the data edits to the database.
        """
        return self.dbconnmanager.confirm_before_saving_edits()

    def set_confirm_before_saving_edits(self, x):
        """
        Set wheter we should ask confirmation to the user before saving
        the data edits to the database.
        """
        self.dbconnmanager.set_confirm_before_saving_edits(x)


class ReadingsTableWidget(SardesTableWidget):

    def __init__(self, table_model, parent):
        super().__init__(table_model, parent, multi_columns_sort=True,
                         sections_movable=False, sections_hidable=False,
                         disabled_actions=['new_row'])
        self.setAttribute(Qt.WA_DeleteOnClose)
        self._parent = parent
        self.plot_viewer = None

    @property
    def station_uuid(self):
        """
        Return the station uuid associated with this table.
        """
        return self.model()._obs_well_uuid

    def update_data(self, dbmanager):
        """
        Update the data of this table's model by using the provided
        database manager.
        """
        self.model().sig_data_about_to_be_updated.emit()
        dbmanager.get(
            'manual_measurements',
            callback=self.set_manual_measurements,
            postpone_exec=True)
        dbmanager.get(
            'repere_data',
            callback=self.set_repere_data,
            postpone_exec=True)
        dbmanager.get_timeseries_for_obs_well(
            self.station_uuid,
            [DataType.WaterLevel, DataType.WaterTemp, DataType.WaterEC],
            callback=self.model().set_model_data,
            postpone_exec=True)
        dbmanager.run_tasks()

    def set_obs_well_data(self, obs_well_data):
        """Set the observation well data of the model and plot viewer."""
        self.model().set_obs_well_data(obs_well_data)
        if self.plot_viewer is not None:
            self.update_plot_viewer_title()

        # Update tools.
        for tool in self.tools():
            tool.update()

    def set_repere_data(self, repere_data):
        """Set the repere data of the model."""
        self.model().set_repere_data(repere_data)

        # Update tools.
        for tool in self.tools():
            tool.update()

    def set_manual_measurements(self, measurements):
        """
        Set the water level manual measurements of the model and plot viewer.
        """
        self.model().set_manual_measurements(measurements)
        if self.plot_viewer is not None:
            self.plot_viewer.set_manual_measurements(
                DataType.WaterLevel, self.model().manual_measurements())

        # Update tools.
        for tool in self.tools():
            tool.update()

    def _handle_data_updated(self):
        """
        Extend SardesTableWidget method to update the plot viewer after
        the data of the model of this table widget were updated.
        """
        if self.plot_viewer is not None:
            self.plot_viewer.update_data(
                self.model().dataf, self.model()._obs_well_data)

            # We need to set the manual measurements again because the axes
            # are completely cleansed from the figure when the data are
            # updated. See cgq-qgc/sardes#409.
            self.plot_viewer.set_manual_measurements(
                DataType.WaterLevel, self.model().manual_measurements())

        super()._handle_data_updated()

    def get_formatted_data(self):
        """Return a dataframe contraining formatted readings data."""
        return format_reading_data(
            self.model().dataf, self.model()._repere_data)

    def plot_readings(self):
        """
        Create and show a timeseries plot viewer to visualize interactively
        the timeseries data contained in tseries_groups.
        """
        if self.plot_viewer is None:
            obs_well_data = self.model()._obs_well_data

            self.plot_viewer = TimeSeriesPlotViewer(parent=None)
            self.plot_viewer.setWindowIcon(get_icon('show_plot'))
            self.update_plot_viewer_title()

            # Set the data of the plot viewer.
            self.plot_viewer.set_data(self.model().dataf, obs_well_data)
            self.plot_viewer.set_manual_measurements(
                DataType.WaterLevel, self.model().manual_measurements())

        if self.plot_viewer.windowState() == Qt.WindowMinimized:
            self.plot_viewer.setWindowState(Qt.WindowNoState)
        self.plot_viewer.show()
        self.plot_viewer.activateWindow()
        self.plot_viewer.raise_()

    def update_plot_viewer_title(self):
        """
        Setup the window title of the plot viewer.
        """
        obs_well_data = self.model()._obs_well_data

        window_title = '{}'.format(obs_well_data['obs_well_id'])
        if obs_well_data['common_name']:
            window_title += ' - {}'.format(obs_well_data['common_name'])
        if obs_well_data['municipality']:
            window_title += ' ({})'.format(obs_well_data['municipality'])
        self.plot_viewer.setWindowTitle(window_title)

    # ---- Qt overrides
    def closeEvent(self, event):
        """Extend Qt closeEvent."""
        if self.plot_viewer is not None:
            self.plot_viewer.close()
            self.plot_viewer = None
        super().closeEvent(event)


class Readings(SardesPlugin):

    CONF_SECTION = 'readings'

    def __init__(self, parent):
        super().__init__(parent)
        self._tseries_table_widgets = {}

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
        return len(self._tseries_table_widgets)

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
            self._handle_tseries_data_changed)
        self.main.db_connection_manager.sig_database_data_changed.connect(
            self._handle_database_data_changed)
        self.main.db_connection_manager.sig_database_disconnected.connect(
            self.tabwidget.close_all_tables)

    def on_docked(self):
        """
        Implement SardesPlugin abstract method.
        """
        # Hide stacked table widget statusbar.
        self.tabwidget.statusBar().hide()

        # Register each table to main.
        for table in self._tseries_table_widgets.values():
            self.main.register_table(table.tableview)

    def on_undocked(self):
        """
        Implement SardesPlugin abstract method.
        """
        # Show stacked table widget statusbar.
        self.tabwidget.statusBar().show()

        # Un-register each table from main.
        for table in self._tseries_table_widgets.values():
            self.main.unregister_table(table.tableview)

    def on_pane_view_toggled(self, toggled):
        """
        Implement SardesPlugin abstract method.
        """
        if toggled is False:
            # Close tools for all tables.
            for table in self._tseries_table_widgets.values():
                for tool in table.tools():
                    tool.close()

    # ---- Private methods
    @Slot(object)
    def _handle_data_table_destroyed(self, obs_well_uuid):
        """
        Handle when a timeseries data table is destroyed.
        """
        self.main.unregister_table(
            self._tseries_table_widgets[obs_well_uuid].tableview)
        del self._tseries_table_widgets[obs_well_uuid]

    # ---- Readings tables
    def view_timeseries_data(self, obs_well_uuid):
        """
        Create and show a table to visualize the timeseries data contained
        in tseries_groups.
        """
        self.switch_to_plugin()
        if obs_well_uuid not in self._tseries_table_widgets:
            self.main.db_connection_manager.get(
                'observation_wells_data',
                callback=lambda obs_wells_data: self._create_readings_table(
                    obs_wells_data.loc[obs_well_uuid])
                )
        else:
            data_table = self._tseries_table_widgets[obs_well_uuid]
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
        table_model = ReadingsTableModel(
            obs_well_data, obs_well_id, obs_well_uuid)
        table_model.set_database_connection_manager(
            self.main.db_connection_manager)

        table_widget = ReadingsTableWidget(table_model, self.main)
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
            triggered=table_widget.plot_readings,
            iconsize=get_iconsize()
            )
        table_widget._actions['plot_data'] = table_widget.add_toolbar_widget(
            show_plot_btn)

        # Add tools to the table.
        table_widget.install_tool(SatisticalHydrographTool(table_widget))

        table_widget.install_tool(HydrographTool(table_widget),
                                  after='copy_to_clipboard')

        table_widget.install_tool(SaveReadingsToExcelTool(table_widget),
                                  after='copy_to_clipboard')

        # Set the title of the window.
        table_widget.setWindowTitle(_("Observation well {} ({})").format(
            obs_well_id, obs_well_data['municipality']))

        # Columns width and minimum window size.
        horizontal_header = table_widget.tableview.horizontalHeader()
        horizontal_header.setDefaultSectionSize(125)

        # Add the table to the tab widget.
        self._tseries_table_widgets[obs_well_uuid] = table_widget
        self.tabwidget.add_table(
            table_widget, obs_well_data['obs_well_id'], switch_to_table=True)
        if self.dockwindow.is_docked():
            self.main.register_table(table_widget.tableview)

        # Fetch and set the data in the table.
        table_widget.update_data(self.main.db_connection_manager)

    # ---- Database Changes Handlers
    def _set_obs_well_data(self, obs_well_data):
        """
        Set the observation well data for all readings tables currently
        opened in Sardes.
        """
        for obs_well_uuid, table in self._tseries_table_widgets.items():
            table.set_obs_well_data(obs_well_data)
        self.tabwidget._update_tab_names()

    def _set_manual_measurements(self, manual_measurements):
        """
        Set the manual measurements for all readings tables currently
        opened in Sardes.
        """
        for obs_well_uuid, table in self._tseries_table_widgets.items():
            table.set_manual_measurements(manual_measurements)

    def _set_repere_data(self, repere_data):
        """
        Set the repere data for all readings tables currently
        opened in Sardes.
        """
        for obs_well_uuid, table in self._tseries_table_widgets.items():
            table.set_repere_data(repere_data)

    def _handle_database_data_changed(self, data_names):
        """
        Handle when data needed by the readings table changed.
        """
        run_tasks = False
        for name in data_names:
            if name in ['manual_measurements']:
                run_tasks = True
                self.main.db_connection_manager.get(
                    'manual_measurements',
                    callback=self._set_manual_measurements,
                    postpone_exec=True)
            if name in ['repere_data']:
                run_tasks = True
                self.main.db_connection_manager.get(
                    'repere_data',
                    callback=self._set_repere_data,
                    postpone_exec=True)
            if name in ['observation_wells_data']:
                run_tasks = True
                self.main.db_connection_manager.get(
                    'observation_wells_data',
                    callback=self._set_obs_well_data,
                    postpone_exec=True)
        if run_tasks is True:
            self.main.db_connection_manager.run_tasks()

    def _handle_tseries_data_changed(self, obs_well_uuids):
        """
        Update the readings tables according to the provided list of
        observation well uuids.
        """
        run_tasks = False
        for obs_well_uuid in obs_well_uuids:
            if obs_well_uuid not in self._tseries_table_widgets:
                continue

            table_widget = self._tseries_table_widgets[obs_well_uuid]
            if table_widget.model()._is_saving_edits:
                continue

            run_tasks = True
            datatypes = [DataType.WaterLevel,
                         DataType.WaterTemp,
                         DataType.WaterEC]
            self.main.db_connection_manager.get_timeseries_for_obs_well(
                obs_well_uuid,
                datatypes,
                callback=table_widget.model().set_model_data,
                postpone_exec=True)

        if run_tasks is True:
            self.main.db_connection_manager.run_tasks()
