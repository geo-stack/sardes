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
from sardes.plugins.obs_wells_explorer.table import ObsWellsTableWidget

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
        self.tablewidget = ObsWellsTableWidget(self.main.db_connection_manager)

        # Restore the state of the observation wells table horizontal header
        # from the configs.
        self.tablewidget.restore_table_horiz_header_state(
            self.get_option('horiz_header/state', None))

        return self.tablewidget

    def close_plugin(self):
        """
        Extend Sardes plugin method to save user inputs in the
        configuration file.
        """
        super().close_plugin()

        # Save in the configs the state of the observation wells table
        # horizontal header.
        self.set_option('horiz_header/state',
                        self.tablewidget.get_table_horiz_header_state())
