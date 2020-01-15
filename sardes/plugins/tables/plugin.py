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

            sort_by_columns, columns_sort_order = (
                table.get_columns_sorting_state())
            CONF.set(table_id, 'horiz_header/sort_by_columns',
                     sort_by_columns)
            CONF.set(table_id, 'horiz_header/columns_sort_order',
                     columns_sort_order)

    def register_plugin(self):
        """
        Extend base class method to do some connection with the database
        manager to update the tables' data.
        """
        super().register_plugin()
        connection_manager = self.main.db_connection_manager
        connection_manager.sig_database_connection_changed.connect(
            self._update_current_table)
        connection_manager.sig_database_data_changed.connect(
            self._update_current_table)

    # ---- Private methods
    def _setup_tables(self):
        self._tables = {}
        self._create_and_register_table(
            ObsWellsTableWidget,
            'observation_wells_data',
            [])
        self._create_and_register_table(
            SondesInventoryTableWidget,
            'sondes_data',
            ['sonde_models_lib'])
        self._create_and_register_table(
            ManualMeasurementsTableWidget,
            'manual_measurements',
            ['observation_wells_data'])

        # Setup the current active tab from the value saved in the configs.
        self.tabwidget.setCurrentIndex(
            self.get_option('last_focused_tab', 0))

    def _create_and_register_table(self, TableClass, data_name, lib_names):
        table = TableClass()
        self.main.db_connection_manager.register_table_model(
            table.model(), data_name, lib_names)

        self._tables[table.get_table_id()] = table
        self.tabwidget.addTab(
            table, get_icon('table'), table.get_table_title())

        # Restore the state of the tables' horizontal header from the configs.
        table.restore_table_horiz_header_state(
            CONF.get(table.get_table_id(), 'horiz_header/state', None))

        sort_by_columns = CONF.get(
            table.get_table_id(), 'horiz_header/sort_by_columns', [])
        columns_sort_order = CONF.get(
            table.get_table_id(), 'horiz_header/columns_sort_order', [])
        table.set_columns_sorting_state(sort_by_columns, columns_sort_order)

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

    def _update_current_table(self, *args, **kargs):
        """Update the current table data and state."""
        if self.current_table().isVisible():
            self.current_table().setEnabled(
                self.main.db_connection_manager.is_connected())
            self.current_table().update_model_data()
