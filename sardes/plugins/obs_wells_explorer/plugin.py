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
from sardes.api.plugins import SardesPlugin
from sardes.api.panes import SardesPaneWidget
from sardes.config.gui import get_iconsize
from sardes.config.locale import _
from sardes.widgets.locationtable import ObservationWellTableView
from sardes.utils.qthelpers import create_toolbutton
from sardes.widgets.timeseries import TimeSeriesPlotViewer
from sardes.utils.qthelpers import create_toolbar_stretcher

"""Observation well explorer plugin"""


class ObsWellsExplorer(SardesPlugin):

    CONF_SECTION = 'obs_wells_explorer'

    def __init__(self, parent):
        super().__init__(parent)

    @classmethod
    def get_plugin_title(cls):
        """Return widget title"""
        return _('Observation Wells')

    def create_pane_widget(self):
        """
        Create and return the pane widget to use in this
        plugin's dockwidget.
        """
        # ---- Setup Observation Well table view
        self.obs_well_tableview = ObservationWellTableView(
            self.main.db_connection_manager)
        self.obs_well_tableview.doubleClicked.connect(
            self._handle_table_double_clicked)

        # Restore the state of the observation wells table horizontal header
        # from the configs.
        self.obs_well_tableview.restore_horiz_header_state(
            self.get_option('horiz_header/state', None))

        pane_widget = SardesPaneWidget(parent=self.main)
        pane_widget.set_central_widget(self.obs_well_tableview)

        # ---- Setup upper toolbar.
        upper_toolbar = pane_widget.get_upper_toolbar()

        show_plot_button = create_toolbutton(
            pane_widget,
            icon='show_plot',
            text=_("Show data"),
            tip=_('Show the data of the timeseries acquired in the currently '
                  'selected observation well in an interactive '
                  'plot viewer.'),
            shortcut='Ctrl+P',
            triggered=lambda _: self._handle_table_double_clicked(),
            iconsize=get_iconsize()
            )
        upper_toolbar.addWidget(show_plot_button)


        upper_toolbar.addWidget(create_toolbar_stretcher())
        upper_toolbar.addWidget(
            self.obs_well_tableview.get_column_options_button())

        return pane_widget

    def get_current_obs_well(self):
        """
        Return the observation well id relative to the currently selected
        row in the table.
        """
        try:
            proxy_index = (self.obs_well_tableview
                           .selectionModel()
                           .selectedIndexes()[0])
            model_index = (self.obs_well_tableview
                           .obs_well_proxy_model
                           .mapToSource(proxy_index))
            obs_well_id = (self.obs_well_tableview
                           .obs_well_table_model.obs_wells
                           .iloc[model_index.row()]['obs_well_id'])
        except IndexError:
            # This means that no row is currently selected in the table.
            obs_well_id = None
        return obs_well_id

    # ---- Timeseries
    def _handle_table_double_clicked(self, *args, **kargs):
        """
        Handle when a row is double-clicked in the table.
        """
        current_obs_well = self.get_current_obs_well()
        if current_obs_well is not None:
            QApplication.setOverrideCursor(Qt.WaitCursor)

            # Get the timeseries data for that observation well.
            self.main.db_connection_manager.get_timeseries_for_obs_well(
                current_obs_well, ['NIV_EAU', 'TEMP'], self._show_timeseries)

    def _show_timeseries(self, tseries_groups):
        """
        Create and show a timeseries plot viewer to visualize interactively
        the timeseries data contained in tseries_list.
        """
        viewer = TimeSeriesPlotViewer(self.obs_well_tableview)

        # Set the title of the window.
        viewer.setWindowTitle(
            _("Observation well {}").format(self.get_current_obs_well()))

        # Setup the water level axe.
        # where = 'left'
        for tseries_group in tseries_groups:
            # Create a new axe to hold the timeseries for the monitored
            # property related to this group of timeseries.
            viewer.create_axe(tseries_group)

        QApplication.restoreOverrideCursor()
        viewer.show()

    def close_plugin(self):
        """
        Extend Sardes plugin method to save user inputs in the
        configuration file.
        """
        super().close_plugin()

        # Save in the configs the state of the observation wells table
        # horizontal header.
        self.set_option('horiz_header/state',
                        self.obs_well_tableview.get_horiz_header_state())
