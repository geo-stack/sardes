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
from qtpy.QtCore import Qt, Slot
from qtpy.QtWidgets import QApplication

# ---- Local imports
from sardes.api.tablemodels import SardesTableModel
from sardes.api.timeseries import DataType, merge_timeseries_groups
from sardes.widgets.timeseries import TimeSeriesPlotViewer
from sardes.config.gui import get_iconsize
from sardes.config.locale import _
from sardes.utils.qthelpers import create_toolbutton
from sardes.widgets.tableviews import (
    SardesTableWidget, StringEditDelegate, BoolEditDelegate,
    NumEditDelegate, NotEditableDelegate, TextEditDelegate)


class ObsWellsTableModel(SardesTableModel):
    """
    A table model to display the list of observation wells that are saved
    in the database.
    """

    def create_delegate_for_column(self, view, column):
        """
        Create the item delegate that the view need to use when editing the
        data of this model for the specified column. If None is returned,
        the items of the column will not be editable.
        """
        if column in ['is_station_active']:
            return BoolEditDelegate(view, is_required=True)
        elif column in ['obs_well_id']:
            return StringEditDelegate(view, unique_constraint=True,
                                      is_required=True)
        elif column in ['municipality', 'is_influenced', 'common_name',
                        'in_recharge_zone', 'confinement', 'aquifer_type',
                        'aquifer_code']:
            return StringEditDelegate(view)
        elif column in ['obs_well_notes']:
            return TextEditDelegate(view)
        elif column in ['latitude', 'longitude']:
            return NumEditDelegate(view, 16, -180, 180)
        else:
            return NotEditableDelegate(self)

    # ---- Visual Data
    def logical_to_visual_data(self, visual_dataf):
        """
        Transform logical data to visual data.
        """
        try:
            obs_wells_stats = self.libraries['observation_wells_statistics']
        except KeyError:
            pass
        else:
            for column in ['first_date', 'last_date', 'mean_water_level']:
                if column in obs_wells_stats.columns:
                    visual_dataf[column] = obs_wells_stats[column]
        return visual_dataf


class DataTableModel(SardesTableModel):
    def __init__(self, obs_well_uuid):
        super().__init__('Timeseries Data', 'tseries_data', [])
        self._obs_well_uuid = obs_well_uuid

    def create_delegate_for_column(self, view, column):
        if column in DataType:
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

        for edit in self._datat.edits():
            row_data = self._datat.get(edit.row)
            indexes = (row_data['datetime'], row_data['obs_id'], edit.column)
            tseries_edits.loc[indexes, 'value'] = edit.edited_value

        self.db_connection_manager.save_timeseries_data_edits(
            tseries_edits, self._handle_data_edits_saved)

    def _handle_data_edits_saved(self):
        """
        Handle when data edits were all saved in the database.
        """
        self.update_data()


class ObsWellsTableWidget(SardesTableWidget):

    def __init__(self, parent=None):
        table_model = ObsWellsTableModel(
            table_title=_('Observation Wells'),
            table_id='table_observation_wells',
            data_columns_mapper=[
                ('obs_well_id', _('Well ID')),
                ('common_name', _('Common Name')),
                ('municipality', _('Municipality')),
                ('aquifer_type', _('Aquifer')),
                ('aquifer_code', _('Aquifer Code')),
                ('confinement', _('Confinement')),
                ('in_recharge_zone', _('Recharge Zone')),
                ('is_influenced', _('Influenced')),
                ('latitude', _('Latitude')),
                ('longitude', _('Longitude')),
                ('first_date', _('First Date')),
                ('last_date', _('Last Date')),
                ('mean_water_level', _('Mean level (m)')),
                ('is_station_active', _('Active')),
                ('obs_well_notes', _('Notes'))]
            )
        super().__init__(table_model, parent)
        self.data_tables = {}

        self.add_toolbar_separator()
        for button in self._create_extra_toolbuttons():
            self.add_toolbar_widget(button)

    # ---- Timeseries
    def get_current_obs_well_data(self):
        """
        Return the observation well data relative to the currently selected
        rows in the table.
        """
        return self.tableview.get_current_row_data().iloc[0]

    def _create_extra_toolbuttons(self):
        show_plot_btn = create_toolbutton(
            self,
            icon='show_plot',
            text=_("Plot data"),
            tip=_('Show the data of the timeseries acquired in the currently '
                  'selected observation well in an interactive '
                  'plot viewer.'),
            triggered=lambda _: self._plot_current_obs_well_data(),
            iconsize=get_iconsize()
            )
        show_data_btn = create_toolbutton(
            self,
            icon='show_data_table',
            text=_("View data"),
            tip=_('Show the data of the timeseries acquired in the currently '
                  'selected observation well in a table.'),
            triggered=lambda _: self.view_timeseries_data(),
            iconsize=get_iconsize()
            )
        return [show_plot_btn, show_data_btn]

    @Slot()
    def _plot_current_obs_well_data(self):
        """
        Handle when a request has been made to show the data of the currently
        selected well in a plot.
        """
        self.tableview.setFocus()
        current_obs_well = self.get_current_obs_well_data()
        if current_obs_well is not None:
            QApplication.setOverrideCursor(Qt.WaitCursor)

            # Get the timeseries data for that observation well.
            self.db_connection_manager.get_timeseries_for_obs_well(
                current_obs_well.name,
                [DataType.WaterLevel, DataType.WaterTemp, DataType.WaterEC],
                self.plot_timeseries_data)

    def view_timeseries_data(self):
        """
        Create and show a table to visualize the timeseries data contained
        in tseries_groups.
        """
        self.tableview.setFocus()
        current_obs_well_data = self.get_current_obs_well_data()
        if current_obs_well_data is None:
            return
        if current_obs_well_data.name not in self.data_tables:
            # Setup a new table model and widget.
            table_model = DataTableModel(current_obs_well_data.name)
            table_model.set_database_connection_manager(
                self.db_connection_manager)
            table_widget = SardesTableWidget(
                table_model, parent=self, multi_columns_sort=True,
                sections_movable=False, sections_hidable=False,
                disabled_actions=['new_row'])
            table_widget.setAttribute(Qt.WA_DeleteOnClose)
            table_widget.destroyed.connect(
                lambda: self._handle_data_table_destroyed(
                    current_obs_well_data.name))

            # Set the title of the window.
            table_widget.setWindowTitle(_("Observation well {} ({})").format(
                current_obs_well_data['obs_well_id'],
                current_obs_well_data['municipality'])
                )

            # Columns width and minimum window size.
            horizontal_header = table_widget.tableview.horizontalHeader()
            horizontal_header.setDefaultSectionSize(100)
            table_widget.resize(475, 600)

            self.data_tables[current_obs_well_data.name] = table_widget
            table_model.update_data()
        data_table = self.data_tables[current_obs_well_data.name]
        data_table.show()
        data_table.raise_()
        if data_table.windowState() == Qt.WindowMinimized:
            # Window is minimised. Restore it.
            data_table.setWindowState(Qt.WindowNoState)
        data_table.setFocus()

    def _handle_data_table_destroyed(self, obs_well_uuid):
        """
        Handle when a timeseries data table is destroyed.
        """
        del self.data_tables[obs_well_uuid]

    def plot_timeseries_data(self, tseries_groups):
        """
        Create and show a timeseries plot viewer to visualize interactively
        the timeseries data contained in tseries_groups.
        """
        viewer = TimeSeriesPlotViewer(self)

        # Set the title of the window.
        current_obs_well_data = self.get_current_obs_well_data()
        viewer.setWindowTitle(_("Observation well {} ({})").format(
            current_obs_well_data['obs_well_id'],
            current_obs_well_data['municipality'])
            )

        # Setup the data for the timeseries plot viewer.
        # where = 'left'
        for tseries_group in tseries_groups[:2]:
            # Create a new axe to hold the timeseries for the monitored
            # property related to this group of timeseries.
            viewer.create_axe(tseries_group)

        QApplication.restoreOverrideCursor()
        viewer.show()
