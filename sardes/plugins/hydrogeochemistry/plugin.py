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
from sardes.tables import (
    PurgesTableWidget, HGSurveysTableWidget, HGParamValuesTableWidget)
from .hgsurveys import HGSurveyImportManager

"""Hydrogeochemistry plugin"""


class Hydrogeochemistry(SardesPlugin):

    CONF_SECTION = 'hydrogeochemistry'

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
        return _('Hydrogeochemistry')

    def create_pane_widget(self):
        """
        Create and return the pane widget to use in this plugin's dockwidget.
        """
        self.tabwidget = SardesStackedTableWidget(self.main)
        return self.tabwidget

    def __post_init__(self):
        self._tables = {}
        self._setup_tables()

        self.hgsurvey_import_manager = HGSurveyImportManager()
        self.hgsurvey_import_manager.install_manager(self)

    def close_plugin(self):
        """
        Extend Sardes plugin method to save user inputs in the
        configuration file.
        """
        super().close_plugin()

        # Save the currently active tab index.
        self.set_option('last_focused_tab', self.tabwidget.currentIndex())

        # Save in the configs the state of the tables.
        for table_name, table in self._tables.items():
            sort_by_columns, columns_sort_order = (
                table.get_columns_sorting_state())

            CONF.set(table_name,
                     'horiz_header/state',
                     table.get_table_horiz_header_state())
            CONF.set(table_name, 'horiz_header/sort_by_columns',
                     sort_by_columns)
            CONF.set(table_name, 'horiz_header/columns_sort_order',
                     columns_sort_order)

            table.close()

        # Close the hgsurvey import manager.
        self.hgsurvey_import_manager.close_manager()

    def register_plugin(self):
        """
        Extend base class method to do some connection with the database
        manager to update the tables' data.
        """
        super().register_plugin()
        self.main.table_models_manager.sig_models_data_changed.connect(
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
        self._create_and_register_table(HGSurveysTableWidget)
        self._create_and_register_table(PurgesTableWidget)
        self._create_and_register_table(HGParamValuesTableWidget)

        # Setup the current active tab from the value saved in the configs.
        self.tabwidget.setCurrentIndex(self.get_option('last_focused_tab', 0))

    def _create_and_register_table(self, TableClass):
        print('Setting up table {}...'.format(TableClass.__name__))
        table = TableClass()

        self.main.table_models_manager.register_table_model(table.model())
        table.register_to_plugin(self)

        self._tables[table.table_name()] = table
        self.tabwidget.add_table(table, table.table_title())

        # Restore the state of the tables' horizontal header from the configs.
        table.restore_table_horiz_header_state(
            CONF.get(table.table_name(), 'horiz_header/state', None))

        sort_by_columns = CONF.get(
            table.table_name(), 'horiz_header/sort_by_columns', [])
        columns_sort_order = CONF.get(
            table.table_name(), 'horiz_header/columns_sort_order', [])
        table.set_columns_sorting_state(sort_by_columns, columns_sort_order)

        # Connect signals.
        table.tableview.sig_show_event.connect(self._update_current_table)

    def _update_current_table(self, *args, **kargs):
        """Update the current table data and state."""
        if self.current_table().isVisible():
            self.current_table().setEnabled(
                self.main.db_connection_manager.is_connected())
            self.current_table().update_model_data()
