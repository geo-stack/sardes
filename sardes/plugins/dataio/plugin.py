# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports

# ---- Third party imports

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

    def register_plugin(self):
        """
        Extend base class method to do some connection with the database
        manager to update the tables' data.
        """
        super().register_plugin()
        self.main.db_connection_manager.register_model(
            self.data_import_wizard,
            'sondes_data',
            ['sonde_models_lib', 'sonde_installations',
             'observation_wells_data'])

        # Set the import wizard working dir.
        self.data_import_wizard.working_directory = self.get_option(
            'wiz_workdir', None)

    # ---- Private API
    def _show_data_import_wizard(self):
        self._update_data_import_wizard()
        self.data_import_wizard.show()

    def _update_data_import_wizard(self):
        self.main.db_connection_manager.update_model('data_import_wizard')
