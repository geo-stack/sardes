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
from sardes.utils.qthelpers import create_mainwindow_toolbar, create_toolbutton


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

    def setup_plugin(self):
        """Setup this plugin."""
        self.data_import_wizard = DataImportWizard(self.main)
        self.data_import_wizard.sig_view_data.connect(
            self.main.tables_plugin.view_timeseries_data)
        self.data_import_wizard.set_database_connection_manager(
            self.main.db_connection_manager)

    def create_mainwindow_toolbars(self):
        toolbar = create_mainwindow_toolbar("Data Import Wizard toolbar")

        # Setup the database connection button.
        data_import_button = create_toolbutton(
            self.main, triggered=self._show_data_import_wizard,
            text=_("Import Data..."),
            tip=_("Open a wizard to import new monitoring data."),
            icon='file_import'
            )
        toolbar.addWidget(data_import_button)

        return [toolbar]

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
        self.data_import_wizard.pathbox_widget.checkbox.setChecked(
            self.get_option('move_inputfile_enabled', False))

    # ---- Private API
    def _show_data_import_wizard(self):
        self.data_import_wizard.show()
