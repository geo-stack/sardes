# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Local imports
from .widgets import DataImportWizard
from sardes.api.plugins import SardesPlugin
from sardes.config.locale import _


"""Data Input/Output plugin"""


class DataIO(SardesPlugin):

    CONF_SECTION = 'data_io'

    def __init__(self, parent):
        super().__init__(parent)

    # ---- SardesPlugin Public API
    @classmethod
    def get_plugin_title(cls):
        """Return widget title"""
        return _('Data Import Wizard')

    def create_pane_widget(self):
        return self.data_import_wizard

    def setup_plugin(self):
        """Setup this plugin."""
        self.data_import_wizard = DataImportWizard(self.main)
        self.data_import_wizard.sig_view_data.connect(
            self.main.view_timeseries_data)
        self.data_import_wizard.set_database_connection_manager(
            self.main.db_connection_manager)

    def close_plugin(self):
        """
        Extend Sardes plugin method to save user inputs in the
        configuration file.
        """
        super().close_plugin()

        # Save the import wizard working dir.
        self.set_option(
            'wiz_workdir', self.data_import_wizard.working_directory)

        # Save the path and working directory for the wizard move input
        # files after loading option.
        self.set_option(
            'move_inputfile_path',
            self.data_import_wizard.pathbox_widget.path())
        self.set_option(
            'move_inputfile_workdir',
            self.data_import_wizard.pathbox_widget.workdir())
        self.set_option(
            'move_inputfile_enabled',
            self.data_import_wizard.pathbox_widget.is_enabled())

        # Save the state of the horizontal header.
        self.data_import_wizard.clear_table()
        self.set_option(
            'horiz_header/state',
            self.data_import_wizard.table_widget.get_table_horiz_header_state()
            )

        self.data_import_wizard.close()

    def register_plugin(self):
        """
        Extend base class method to do some connection with the database
        manager to update the tables' data.
        """
        super().register_plugin()

        # Set the import wizard working dir.
        self.data_import_wizard.working_directory = self.get_option(
            'wiz_workdir', None)

        # Set the options for the feature to move files after loading data.
        self.data_import_wizard.pathbox_widget.set_path(self.get_option(
            'move_inputfile_path', ''))
        self.data_import_wizard.pathbox_widget.set_workdir(self.get_option(
            'move_inputfile_workdir', ''))
        self.data_import_wizard.pathbox_widget.set_enabled(
            self.get_option('move_inputfile_enabled', False))

        # Restore the state of the horizontal header.
        self.data_import_wizard.table_widget.restore_table_horiz_header_state(
            self.get_option('horiz_header/state', None))

    def on_docked(self):
        """
        Implement SardesPlugin abstract method.
        """
        # Register data import wizard table to main and hide its statusbar.
        self.data_import_wizard.table_widget.statusBar().hide()
        self.main.register_table(
            self.data_import_wizard.table_widget.tableview)

    def on_undocked(self):
        """
        Implement SardesPlugin abstract method.
        """
        # Un-register data import wizard table from main and show
        # its statusbar.
        self.data_import_wizard.table_widget.statusBar().show()
        self.main.unregister_table(
            self.data_import_wizard.table_widget.tableview)
