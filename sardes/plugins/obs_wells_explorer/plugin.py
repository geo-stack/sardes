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
from sardes.api.panes import SardesPaneWidget
from sardes.config.locale import _
from sardes.widgets.locationtable import ObservationWellTableView

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
        pane_widget = SardesPaneWidget(parent=self.main)
        pane_widget.set_central_widget(
            ObservationWellTableView(self.main.db_connection_manager))
        return pane_widget
