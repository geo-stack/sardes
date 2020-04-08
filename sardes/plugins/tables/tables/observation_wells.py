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
from qtpy.QtCore import Qt, Signal, Slot
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
            return NotEditableDelegate(view)

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


class ObsWellsTableWidget(SardesTableWidget):
    sig_view_data = Signal(object)

    def __init__(self, *args, **kargs):
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
        super().__init__(table_model, *args, **kargs)

        self.add_toolbar_separator()
        for button in self._create_extra_toolbuttons():
            self.add_toolbar_widget(button)

    # ---- SardesPaneWidget public API
    def register_to_plugin(self, plugin):
        """Register this table with the given plugin."""
        self.sig_view_data.connect(plugin.view_timeseries_data)

    # ---- Timeseries
    def get_current_obs_well_data(self):
        """
        Return the observation well data relative to the currently selected
        rows in the table.
        """
        try:
            return self.tableview.get_current_row_data().iloc[0]
        except AttributeError:
            return None

    def _create_extra_toolbuttons(self):
        self.show_plot_btn = create_toolbutton(
            self,
            icon='show_plot',
            text=_("Plot data"),
            tip=_('Show the data of the timeseries acquired in the currently '
                  'selected observation well in an interactive '
                  'plot viewer.'),
            triggered=lambda _: self._plot_current_obs_well_data(),
            iconsize=get_iconsize()
            )
        self.show_data_btn = create_toolbutton(
            self,
            icon='show_data_table',
            text=_("View data"),
            tip=_('Show the data of the timeseries acquired in the currently '
                  'selected observation well in a table.'),
            triggered=lambda _: self._view_current_timeseries_data(),
            iconsize=get_iconsize()
            )
        return [self.show_plot_btn, self.show_data_btn]

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

    def _view_current_timeseries_data(self):
        """
        Emit a signal to show the timeseries data saved in the database for
        the currently selected observation well in the table.
        """
        current_obs_well_data = self.get_current_obs_well_data()
        if current_obs_well_data is not None:
            self.sig_view_data.emit(current_obs_well_data.name)

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
