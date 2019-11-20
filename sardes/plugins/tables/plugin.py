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
    ObsWellsTableWidget, SondesInventoryTableWidget,
    ManualMeasurementsTableWidget)

# ---- Third party imports
from qtpy.QtCore import Qt, QSize
from qtpy.QtWidgets import QApplication, QFileDialog, QTabWidget

# ---- Local imports
from sardes.config.main import CONF


"""Tables plugin"""


class Tables(SardesPlugin):

    CONF_SECTION = 'tables'

    def __init__(self, parent):
        super().__init__(parent)
        self._setup_tables()

    # ---- Public methods implementation
    def current_table(self):
        """
        Return the currently visible table of this plugin.
        """
        return self.tabwidget.currentWidget()

    def table_count(self):
        """
        Return the number of tables installed this plugin.
        """
        return len(self._tables)

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
        self.tabwidget.setIconSize(QSize(18, 18))
        self.tabwidget.setStyleSheet("QTabWidget::pane { "
                                     "margin: 1px,1px,1px,1px;"
                                     "padding: 0px;"
                                     "}"
                                     "QTabBar::tab { height: 30px;}")
        return self.tabwidget

    def close_plugin(self):
        """
        Extend Sardes plugin method to save user inputs in the
        configuration file.
        """
        super().close_plugin()

        # Save the currently active tab index.
        self.set_option('last_focused_tab', self.tabwidget.currentIndex())

        # Save in the configs the state of the tables.
        for table_id, table in self._tables.items():
            CONF.set(table_id, 'horiz_header/state',
                     table.get_table_horiz_header_state())
            CONF.set(table_id, 'horiz_header/sorting',
                     table.tableview.get_columns_sorting_state())

    def register_plugin(self):
        """
        Extend base class method to do some connection with the database
        manager to update the tables' data.
        """
        super().register_plugin()
        connection_manager = self.main.db_connection_manager
        connection_manager.sig_database_connection_changed.connect(
            self._handle_database_connection_changed)
        connection_manager.sig_database_data_changed.connect(
            self._handle_database_changed)

    # ---- Private methods
    def _setup_tables(self):
        self._tables = {}
        self._table_updates = {}
        self._create_and_register_table(ObsWellsTableWidget)
        self._create_and_register_table(SondesInventoryTableWidget)
        self._create_and_register_table(ManualMeasurementsTableWidget)

        # Setup the current active tab from the value saved in the configs.
        self.tabwidget.setCurrentIndex(
            self.get_option('last_focused_tab', 0))

    def _create_and_register_table(self, TableClass):
        table = TableClass(self.main.db_connection_manager)
        self._tables[table.get_table_id()] = table
        self._table_updates[table.get_table_id()] = []
        self.tabwidget.addTab(
            table, get_icon('table'), table.get_table_title())

        # Restore the state of the tables' horizontal header from the configs.
        table.restore_table_horiz_header_state(
            CONF.get(table.get_table_id(), 'horiz_header/state', None))
        table.tableview.sort_by_column(
            *CONF.get(table.get_table_id(), 'horiz_header/sorting', (-1, 0)))

        # Connect signals.
        table.tableview.sig_data_edited.connect(self._update_tab_names)
        table.tableview.sig_show_event.connect(self._update_current_table)

    def _update_tab_names(self):
        """
        Append a '*' symbol at the end of a tab name when its corresponding
        table have unsaved edits.
        """
        for index in range(self.tabwidget.count()):
            table = self.tabwidget.widget(index)
            tab_text = table.get_table_title()
            if table.tableview.model().has_unsaved_data_edits():
                tab_text += '*'
            self.tabwidget.setTabText(index, tab_text)

    def _handle_database_connection_changed(self, is_connected_to_db):
        """
        Handle when a change is made to the database manager connection.
        """
        if is_connected_to_db:
            for table_id, table in self._tables.items():
                self._table_updates[table_id] = table.model().req_data_names()
            self._update_current_table()
        else:
            for table_id, table in self._tables.items():
                self._table_updates[table_id] = []
                table.fetch_model_data()

    def _handle_database_changed(self, data_names):
        """
        Handle when changes are made to the database by the manager.

        Note that changes made to the database outside of Sardes are not
        taken into account here.
        """
        for table_id, table in self._tables.items():
            self._table_updates[table_id].extend(
                [name for name in data_names if
                 name in table.model().req_data_names()])
            self._table_updates[table_id] = list(set(
                self._table_updates[table_id]))
        self._update_current_table()

    def _update_current_table(self):
        """
        Update the current table required data that were changed
        since that table was last updated.
        """
        if self.current_table().isVisible():
            self.current_table().model().update_model_data(
                self._table_updates[self.current_table().get_table_id()])
            self._table_updates[self.current_table().get_table_id()] = []
