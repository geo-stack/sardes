# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Local imports
from sardes.config.main import CONF
from sardes.api.plugins import SardesPlugin
from sardes.config.locale import _
from sardes.widgets.tableviews import SardesStackedTableWidget
from sardes.plugins.tables.tables import (
    ObsWellsTableWidget, RepereTableWidget, SondesInventoryTableWidget,
    ManualMeasurementsTableWidget, SondeInstallationsTableWidget)


"""Tables plugin"""


class Tables(SardesPlugin):

    CONF_SECTION = 'tables'

    def __init__(self, parent):
        super().__init__(parent)
        self._tables = {}
        self._setup_tables()

    # ---- SardesPlugin public API
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
        self.tabwidget = SardesStackedTableWidget(self.main)
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
        self.main.db_connection_manager.sig_models_data_changed.connect(
            self._update_current_table)

    def on_docked(self):
        """
        Implement SardesPlugin abstract method.
        """
        # Hide stacked table widget statusbar.
        self.tabwidget.statusBar().hide()

        # Register each table to main.
        for table in self._tables.values():
            self.main.register_table(table.tableview)

    def on_undocked(self):
        """
        Implement SardesPlugin abstract method.
        """
        # Show stacked table widget statusbar.
        self.tabwidget.statusBar().show()

        # Un-register each table from main.
        for table in self._tables.values():
            self.main.unregister_table(table.tableview)

    # ---- Private methods
    def _setup_tables(self):
        self._create_and_register_table(
            ObsWellsTableWidget,
            data_name='observation_wells_data',
            lib_names=['observation_wells_data_overview',
                       'stored_attachments_info'],
            disabled_actions=['delete_row'])
        self._create_and_register_table(
            SondesInventoryTableWidget,
            data_name='sondes_data',
            lib_names=['sonde_models_lib'],
            disabled_actions=['delete_row'])
        self._create_and_register_table(
            ManualMeasurementsTableWidget,
            data_name='manual_measurements',
            lib_names=['observation_wells_data'])
        self._create_and_register_table(
            SondeInstallationsTableWidget,
            data_name='sonde_installations',
            lib_names=['observation_wells_data',
                       'sondes_data',
                       'sonde_models_lib'],
            disabled_actions=['delete_row'])
        self._create_and_register_table(
            RepereTableWidget,
            data_name='repere_data',
            lib_names=['observation_wells_data'],
            disabled_actions=['delete_row'])

        # Setup the current active tab from the value saved in the configs.
        self.tabwidget.setCurrentIndex(
            self.get_option('last_focused_tab', 0))

    def _create_and_register_table(self, TableClass, data_name, lib_names,
                                   disabled_actions=None):
        table = TableClass(disabled_actions=disabled_actions)

        self.main.db_connection_manager.register_model(
            table.model(), data_name, lib_names)
        table.register_to_plugin(self)

        self._tables[table.get_table_id()] = table
        self.tabwidget.add_table(table, table.get_table_title())

        # Restore the state of the tables' horizontal header from the configs.
        table.restore_table_horiz_header_state(
            CONF.get(table.get_table_id(), 'horiz_header/state', None))

        sort_by_columns = CONF.get(
            table.get_table_id(), 'horiz_header/sort_by_columns', [])
        columns_sort_order = CONF.get(
            table.get_table_id(), 'horiz_header/columns_sort_order', [])
        table.set_columns_sorting_state(sort_by_columns, columns_sort_order)

        # Connect signals.
        table.tableview.sig_show_event.connect(self._update_current_table)

    def _update_current_table(self, *args, **kargs):
        """Update the current table data and state."""
        if self.current_table().isVisible():
            self.current_table().setEnabled(
                self.main.db_connection_manager.is_connected())
            self.current_table().update_model_data()
