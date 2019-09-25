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
from qtpy.QtWidgets import QApplication


# ---- Local imports
from sardes.widgets.tableviews import (
    SardesTableModel, StringEditDelegate, BoolEditDelegate, NumEditDelegate,
    NotEditableDelegate, TextEditDelegate)
from sardes.widgets.timeseries import TimeSeriesPlotViewer
from sardes.config.gui import get_iconsize
from sardes.config.locale import _
from sardes.widgets.tableviews import SardesTableWidget
from sardes.utils.qthelpers import create_toolbutton


class ObsWellsTableModel(SardesTableModel):
    """
    A table model to display the list of observation wells that are saved
    in the database.
    """
    # A list of tuple that maps the keys of the columns dataframe with their
    # corresponding human readable label to use in the GUI.
    __data_columns_mapper__ = [
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
        ('is_station_active', _('Active')),
        ('obs_well_notes', _('Note'))
        ]

    def fetch_model_data(self, *args, **kargs):
        """
        Fetch the observation well data for this table model.
        """
        self.db_connection_manager.get_observation_wells_data(
            callback=self.set_model_data)

    # ---- Delegates
    def create_delegate_for_column(self, view, column):
        """
        Create the item delegate that the view need to use when editing the
        data of this model for the specified column. If None is returned,
        the items of the column will not be editable.
        """
        if column in ['is_station_active']:
            return BoolEditDelegate(view)
        elif column in ['obs_well_id']:
            return StringEditDelegate(view, unique_constraint=True)
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

    # ---- Data edits
    def save_data_edits(self):
        """
        Save all data edits to the database.
        """
        for edit in self._dataf_edits:
            if edit.type() == self.ValueChanged:
                self.db_connection_manager.save_observation_well_data(
                    edit.dataf_index, edit.dataf_column,
                    edit.edited_value, postpone_exec=True)
        self.db_connection_manager.run_tasks()


class ObsWellsTableWidget(SardesTableWidget):
    def __init__(self, db_connection_manager, parent=None):
        table_model = ObsWellsTableModel(db_connection_manager)
        super().__init__(table_model, parent)

        self.add_toolbar_separator()
        self.add_toolbar_widget(self._create_show_data_button())

    # ---- Timeseries
    def get_current_obs_well_data(self):
        """
        Return the observation well data relative to the currently selected
        row in the table.
        """
        return self.tableview.get_selected_row_data()

    def _create_show_data_button(self):
        toolbutton = create_toolbutton(
            self,
            icon='show_plot',
            text=_("Show data"),
            tip=_('Show the data of the timeseries acquired in the currently '
                  'selected observation well in an interactive '
                  'plot viewer.'),
            shortcut='Ctrl+P',
            triggered=lambda _: self._show_timeseries_plot_viewer(),
            iconsize=get_iconsize()
            )
        return toolbutton

    def _show_timeseries_plot_viewer(self, *args, **kargs):
        """
        Handle when a row is double-clicked in the table.
        """
        current_obs_well = self.get_current_obs_well_data()
        if current_obs_well is not None:
            QApplication.setOverrideCursor(Qt.WaitCursor)

            # Get the timeseries data for that observation well.
            self.db_connection_manager.get_timeseries_for_obs_well(
                current_obs_well.index.values[0],
                ['NIV_EAU', 'TEMP'],
                self._show_timeseries)

    def _show_timeseries(self, tseries_groups):
        """
        Create and show a timeseries plot viewer to visualize interactively
        the timeseries data contained in tseries_groups.
        """
        viewer = TimeSeriesPlotViewer(self)

        # Set the title of the window.
        current_obs_well_data = self.get_current_obs_well_data().iloc[0]
        viewer.setWindowTitle(_("Observation well {} ({})").format(
            current_obs_well_data['obs_well_id'],
            current_obs_well_data['municipality'])
            )

        # Setup the water level axe.
        # where = 'left'
        for tseries_group in tseries_groups:
            # Create a new axe to hold the timeseries for the monitored
            # property related to this group of timeseries.
            viewer.create_axe(tseries_group)

        QApplication.restoreOverrideCursor()
        viewer.show()
