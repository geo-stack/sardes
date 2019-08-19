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
from sardes.config.locale import _
from sardes.widgets.locationtable import ObservationWellTableView
from sardes.widgets.timeseries import TimeSeriesPlotViewer

"""Observation well explorer plugin"""


class ObsWellsExplorer(SardesPlugin):

    def __init__(self, parent):
        super().__init__(parent)

    def get_plugin_title(self):
        """Return widget title"""
        return _('Observation Wells')

    def create_pane_widget(self):
        """
        Create and return the pane widget to use in this
        plugin's dockwidget.
        """
        self.obs_well_tableview = ObservationWellTableView(
            self.main.db_connection_manager)
        self.obs_well_tableview.doubleClicked.connect(
            self._handle_table_double_clicked)

        pane_widget = SardesPaneWidget(parent=self.main)
        pane_widget.set_central_widget(self.obs_well_tableview)

        return pane_widget

    def _handle_table_double_clicked(self, proxy_index):
        """
        Handle when a row is double-clicked in the table.
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        model_index = (self.obs_well_tableview
                       .obs_well_proxy_model
                       .mapToSource(proxy_index))
        obs_well_id = (self.obs_well_tableview
                       .obs_well_table_model.obs_wells
                       .iloc[model_index.row()]['obs_well_id'])

        # Get the timeseries data for that observation well.
        self.main.db_connection_manager.get_timeseries_for_obs_well(
            obs_well_id, ['NIV_EAU', 'TEMP'], self._show_timeseries)

    def _show_timeseries(self, tseries_dict):
        """
        Create and show a timeseries plot viewer to visualize interactively
        the timeseries data contained in tseries_list.
        """
        viewer = TimeSeriesPlotViewer(self.obs_well_tableview)

        # Setup the water level axe.
        axe = viewer.create_axe(_('Water level (m)'), 'left')
        for tseries in tseries_dict['NIV_EAU']:
            axe.add_timeseries(tseries)

        # Setup the water temperature axe.
        axe = viewer.create_axe(_('Water temperature (\u00B0C)'), 'right')
        for tseries in tseries_dict['TEMP']:
            axe.add_timeseries(tseries)

        QApplication.restoreOverrideCursor()
        viewer.show()
