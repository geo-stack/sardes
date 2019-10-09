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
    ObsWellsTableWidget, SondesInventoryTableWidget)

# ---- Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QFileDialog, QTabWidget

# ---- Local imports
from sardes.config.main import CONF


"""Observation well explorer plugin"""


class Tables(SardesPlugin):

    CONF_SECTION = 'tables'

    def __init__(self, parent):
        super().__init__(parent)
        self._setup_tables()

    # ---- Public methods implementation
    @classmethod
    def get_plugin_title(cls):
        """Return widget title"""
        return _('Tables')

    def create_pane_widget(self):
        """
        Create and return the pane widget to use in this
        plugin's dockwidget.
        """
        self.tabwidget = QTabWidget(self.main)
        self.tabwidget.setTabPosition(self.tabwidget.North)
        self.tabwidget.setStyleSheet("QTabWidget::pane { "
                                     "margin: 0px,0px,0px,0px;"
                                     "padding: 0px;"
                                     "}")
        return self.tabwidget

    def close_plugin(self):
        """
        Extend Sardes plugin method to save user inputs in the
        configuration file.
        """
        super().close_plugin()

        # Save in the configs the state of the tables.
        for table_id, table in self._tables.items():
            CONF.set(table_id, 'horiz_header/state',
                     table.get_table_horiz_header_state())
            CONF.set(table_id, 'horiz_header/sorting',
                     table.tableview.get_columns_sorting_state())

    # ---- Private methods
    def _setup_tables(self):
        self._tables = {}
        self._create_and_register_table(ObsWellsTableWidget)
        self._create_and_register_table(SondesInventoryTableWidget)

    def _create_and_register_table(self, TableClass):
        table = TableClass(self.main.db_connection_manager)
        self._tables[table.get_table_id()] = table
        self.tabwidget.addTab(
            table, get_icon('table'), table.get_table_title())

        # Restore the state of the tables' horizontal header from the configs.
        table.restore_table_horiz_header_state(
            CONF.get(table.get_table_id(), 'horiz_header/state', None))
        table.tableview.sort_by_column(
            *CONF.get(table.get_table_id(), 'horiz_header/sorting', (-1, 0)))
