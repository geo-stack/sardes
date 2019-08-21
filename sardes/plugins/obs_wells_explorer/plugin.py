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

        return pane_widget

    def get_current_obs_well(self):
        """
        Return the observation well id relative to the currently selected
        row in the table.
        """
        proxy_index = (self.obs_well_tableview
                       .selectionModel()
                       .selectedIndexes()[0])
        model_index = (self.obs_well_tableview
                       .obs_well_proxy_model
                       .mapToSource(proxy_index))
        obs_well_id = (self.obs_well_tableview
                       .obs_well_table_model.obs_wells
                       .iloc[model_index.row()]['obs_well_id'])
        return obs_well_id

    # ---- Timeseries
    def _handle_table_double_clicked(self, *args, **kargs):
        """
        Handle when a row is double-clicked in the table.
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        # Get the timeseries data for that observation well.
        self.main.db_connection_manager.get_timeseries_for_obs_well(
            self.get_current_obs_well(),
            ['NIV_EAU', 'TEMP'],
            self._show_timeseries)

    def _show_timeseries(self, monitored_properties):
        """
        Create and show a timeseries plot viewer to visualize interactively
        the timeseries data contained in tseries_list.
        """
        viewer = TimeSeriesPlotViewer(self.obs_well_tableview)

        # Set the title of the window.
        viewer.setWindowTitle(
            _("Observation well {}").format(self.get_current_obs_well()))

        # Setup the water level axe.
        where = 'left'
        for monitored_property in monitored_properties:
            # Create a new axe to hold the monitored property's timeseries.
            axe_ylabel = monitored_property.prop_name
            if monitored_property.prop_units:
                axe_ylabel += ' ({})'.format(monitored_property.prop_units)
            axe = viewer.create_axe(axe_ylabel, where)

            # Add each timeseries to the axe.
            for tseries in monitored_property.timeseries:
                axe.add_timeseries(tseries)
            where = 'right'

        QApplication.restoreOverrideCursor()
        viewer.show()
