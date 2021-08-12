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
from sardes.config.database import get_dbconfig, set_dbconfig
from sardes.config.locale import _
from sardes.utils.qthelpers import (create_mainwindow_toolbar,
                                    create_toolbutton)
from sardes.plugins.databases.widgets import DatabaseConnectionWidget


"""Database plugin"""


class Databases(SardesPlugin):

    CONF_SECTION = 'database'

    def __init__(self, parent):
        super().__init__(parent)

    @classmethod
    def get_plugin_title(cls):
        """Return widget title"""
        return _('Database Connector')

    def setup_plugin(self):
        """Setup this plugin."""
        # Setup the database connection widget.
        database_dialogs = self.setup_database_dialogs()

        self.db_connection_widget = DatabaseConnectionWidget(
            self.main.db_connection_manager,
            database_dialogs,
            self.get_option('auto_connect_to_database'),
            self.get_option('dbtype_last_selected'),
            parent=self.main)
        self.db_connection_widget.hide()

    def setup_database_dialogs(self):
        """Setup Sardes database connection dialogs."""
        database_dialogs = []

        from sardes.database.dialogs import DatabaseConnectDialogSardesLite
        database_dialog = DatabaseConnectDialogSardesLite()
        database_dialog.set_database_kargs(
            get_dbconfig(database_dialog.dbtype_name))
        database_dialogs.append(database_dialog)

        from sardes.database.dialogs import DatabaseConnectDialogRSESQ
        database_dialog = DatabaseConnectDialogRSESQ()
        database_dialog.set_database_kargs(
            get_dbconfig(database_dialog.dbtype_name))
        database_dialogs.append(database_dialog)

        return database_dialogs

    def create_mainwindow_toolbars(self):
        database_toolbar = create_mainwindow_toolbar("Database toolbar")

        # Setup the database connection button.
        self.database_connect_button = create_toolbutton(
            self.main,
            triggered=self.db_connection_widget.show,
            text=_("Connect to database"),
            tip=_("Open a dialog window to manage the "
                  "connection to the database."),
            shortcut='Ctrl+Shift+D',
            icon='database_connect'
            )
        database_toolbar.addWidget(self.database_connect_button)

        self.database_disconnect_button = create_toolbutton(
            self.main,
            triggered=self.main.db_connection_manager.disconnect_from_db,
            text=_("Disconnect database"),
            tip=_("Close the connection with the database."),
            shortcut='Ctrl+Shift+C',
            icon='database_disconnect'
            )
        database_toolbar.addWidget(self.database_disconnect_button)

        # Setup database icon and connect to signal.
        self.update_database_button_state()
        (self.main
         .db_connection_manager
         .sig_database_connection_changed
         .connect(self.update_database_button_state))

        return [database_toolbar]

    def update_database_button_state(self):
        """
        Set the state of the buttons in the database toolbar to show
        whether a database is currently connected or not.
        """
        self.database_disconnect_button.setEnabled(
            self.main.db_connection_manager.is_connected())

    def connect_to_database(self):
        """
        Try connecting to the database whose parameters are specified in the
        database connection widget.
        """
        self.db_connection_widget.connect()

    def save_database_connection_options(self):
        """
        Save database connection options to the user configs.
        """
        # Save the database connection general options.
        for option, value in self.db_connection_widget.get_options().items():
            self.set_option(option, value)

        # Save to the options for each database dialog.
        database_dialogs_options = (
            self.db_connection_widget.get_database_dialogs_options())
        for dbtype_name, database_kargs in database_dialogs_options.items():
            set_dbconfig(dbtype_name, database_kargs)

    def close_plugin(self):
        """
        Extend Sardes plugin method to save user inputs in the
        configuration file.
        """
        super().close_plugin()
        self.save_database_connection_options()
