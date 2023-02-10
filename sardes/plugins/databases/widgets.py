# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Standard imports
import sys

# ---- Third party imports
from qtpy.QtCore import Qt, Slot
from qtpy.QtWidgets import (
    QApplication, QAbstractButton, QCheckBox, QComboBox, QDialog,
    QDialogButtonBox, QHBoxLayout, QLabel, QPushButton, QStackedWidget,
    QVBoxLayout)

# ---- Local imports
from sardes.config.gui import RED
from sardes.config.locale import _
from sardes.widgets.statusbar import ProcessStatusBar


class DatabaseConnectionWidget(QDialog):
    """
    A dialog window to manage the connection to the database.
    """

    def __init__(self, db_connection_manager, database_dialogs=None,
                 auto_connect_to_database=False, dbtype_last_selected=None,
                 parent=None):
        super(DatabaseConnectionWidget, self).__init__(parent)
        self.setWindowTitle(_('Database connection manager'))
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setModal(True)

        self._setup()
        self._register_database_connection_manager(db_connection_manager)

        # Setup the provided database dialogs.
        for dialog in database_dialogs or []:
            self.add_database_dialog(dialog)

        # Setup widget options.
        self.set_auto_connect_to_database(auto_connect_to_database)
        self.set_current_dbtype_name(dbtype_last_selected)

    def _register_database_connection_manager(self, db_connection_manager):
        """
        Connect this widget with the database connection manager.
        """
        self.db_connection_manager = db_connection_manager
        db_connection_manager.sig_database_connected.connect(
            self._handle_database_connected)
        db_connection_manager.sig_database_disconnected.connect(
            self._handle_database_disconnected)
        db_connection_manager.sig_database_is_connecting.connect(
            self._handle_database_is_connecting)

    def _setup(self):
        """
        Setup the dialog.
        """
        # Setup database type selection combobox.
        self.dbtype_combobox = QComboBox()

        dbtype_layout = QHBoxLayout()
        dbtype_layout.addWidget(QLabel(_("Select database type :")))
        dbtype_layout.addWidget(self.dbtype_combobox)
        dbtype_layout.setStretchFactor(self.dbtype_combobox, 1)

        # Setup the status bar.
        self.status_bar = ProcessStatusBar(
            spacing=5,
            icon_valign='top',
            contents_margin=[0, 5, 0, 5])
        self.status_bar.hide()

        # Setup the stacked dialogs widget.
        self.stacked_dialogs = QStackedWidget()
        self.dbtype_combobox.currentIndexChanged.connect(
            self.stacked_dialogs.setCurrentIndex)

        # Setup the dialog button box.
        self.connect_button = QPushButton(_('Connect'))
        self.connect_button.setDefault(True)
        self.close_button = QPushButton(_('Close'))
        self.close_button.setDefault(False)
        self.close_button.setAutoDefault(False)

        # Setup the auto connect to database checkbox.
        self.auto_connect_to_database_checkbox = QCheckBox(_('Auto connect'))
        self.auto_connect_to_database_checkbox.setToolTip(
            format_tooltip(
                text=_('Auto connect'),
                tip=_('Connect automatically to the '
                      'database when starting Sardes.'),
                shortcuts=None)
            )

        button_box = QDialogButtonBox()
        button_box.addButton(self.connect_button, button_box.ApplyRole)
        button_box.addButton(self.close_button, button_box.RejectRole)
        button_box.layout().insertSpacing(1, 100)
        button_box.clicked.connect(self._handle_button_click_event)

        # Setup the main layout.
        main_layout = QGridLayout(self)
        main_layout.addWidget(self.auto_connect_to_database_checkbox, 0, 1)
        main_layout.setRowMinimumHeight(1, 20)
        main_layout.addLayout(dbtype_layout, 2, 0, 1, 2)
        main_layout.addWidget(self.stacked_dialogs, 3, 0, 1, 2)
        main_layout.addWidget(self.status_bar, 4, 0, 1, 2)
        main_layout.addWidget(button_box, 5, 0, 1, 2)
        main_layout.setRowStretch(3, 1)
        main_layout.setColumnStretch(0, 1)
        main_layout.setSizeConstraint(main_layout.SetFixedSize)

    # ---- Options
    def auto_connect_to_database(self):
        """
        Return whether Sardes should try to connect automatically to the
        last opened database on restart.
        """
        return self.auto_connect_to_database_checkbox.isChecked()

    def set_auto_connect_to_database(self, value):
        """
        Set whether Sardes should try to connect automatically to the
        last opened database on restart.
        """
        self.auto_connect_to_database_checkbox.setChecked(bool(value))

    def get_current_dbtype_name(self):
        """
        Return the name of the current database type.
        """
        return self.get_current_database_dialog().dbtype_name

    def set_current_dbtype_name(self, dbtype_name):
        """
        Set the name of the current database type.
        """
        self.set_current_database_dialog(dbtype_name)

    def get_options(self):
        """
        Return a dictionary containing the options that need
        to be saved in user configs.
        """
        return {
            'auto_connect_to_database': self.auto_connect_to_database(),
            'dbtype_last_selected': self.get_current_dbtype_name()
            }

    # ---- Database dialogs
    def add_database_dialog(self, database_dialog):
        self.stacked_dialogs.addWidget(database_dialog)
        self.dbtype_combobox.addItem(database_dialog.dbtype_name)

    def get_current_database_dialog(self):
        return self.stacked_dialogs.currentWidget()

    def set_current_database_dialog(self, dialog_name):
        """
        Set the current database dialog to that of dialog_name.
        """
        dbtype_index = self.dbtype_combobox.findText(dialog_name)
        self.dbtype_combobox.setCurrentIndex(max(0, dbtype_index))

    def get_current_database_accessor(self):
        """
        Return the database accessor of the currently selected database
        dialog if any.
        """
        if self.get_current_database_dialog():
            return (
                self.get_current_database_dialog().create_database_accessor())
        else:
            return None

    def database_dialogs(self):
        return [self.stacked_dialogs.widget(i) for
                i in range(self.stacked_dialogs.count())]

    def get_database_dialogs_options(self):
        """
        Return a dict containing the options of each database dialog registered
        to this database connection widget.
        """
        return {
            dialog.dbtype_name: dialog.get_database_kargs() for
            dialog in self.database_dialogs()
            }

    # ---- Database public methods
    def disconnect(self):
        """
        Close the connection with the database.
        """
        self.db_connection_manager.disconnect_from_db()

    def connect(self):
        """
        Try to connect to the database using the connection parameters
        provided by the user in the gui.
        """
        self.db_connection_manager.connect_to_db(
            self.get_current_database_accessor())

    # ---- GUI update.
    def _update_gui(self, is_connecting, is_connected):
        """
        Update the visibility and state of the gui based on the connection
        status with the database.
        """
        self.stacked_dialogs.setEnabled(not is_connected and not is_connecting)
        self.dbtype_combobox.setEnabled(not is_connected and not is_connecting)
        self.close_button.setEnabled(not is_connecting)
        self.connect_button.setEnabled(not is_connecting)
        self.connect_button.setText(
            _('Disconnect') if is_connected else _('Connect'))

    # ---- Signal handlers
    @Slot(QAbstractButton)
    def _handle_button_click_event(self, button):
        """
        Handle when a button is clicked on the dialog button box.
        """
        if button == self.close_button:
            self.close()
        elif button == self.connect_button:
            if not self.db_connection_manager.is_connected():
                self.connect()
            else:
                self.disconnect()

    @Slot(object, object)
    def _handle_database_connected(self, db_connection, db_connect_error):
        """
        Handle when the database connection worker sucessfully or failed to
        create a new connection with the database.
        """
        if db_connection is None:
            if db_connect_error:
                message = ('<font color="{}">{}:</font> {}'.format(
                    RED, type(db_connect_error).__name__, db_connect_error))
            else:
                message = _("The connection to the database failed.")
            self.status_bar.show_fail_icon(message)
            self.show()
            self.activateWindow()
            self.raise_()
        else:
            message = _("Connected to the database.")
            self.status_bar.show_sucess_icon(message)
            self.close()
        self._update_gui(is_connecting=False,
                         is_connected=db_connection is not None)

    @Slot()
    def _handle_database_disconnected(self):
        """
        Handle when the connection to the database was sucessfully closed.
        """
        self.status_bar.hide()
        self._update_gui(is_connecting=False, is_connected=False)

    @Slot()
    def _handle_database_is_connecting(self):
        """
        Handle when the connection to the database is in progress.
        """
        self._update_gui(is_connecting=True, is_connected=False)
        self.status_bar.show()
        self.status_bar.set_label(_("Connecting to database..."))


if __name__ == '__main__':
    from sardes.database.database_manager import DatabaseConnectionManager
    from sardes.database.dialog_demo import DatabaseConnectDialogDemo

    app = QApplication(sys.argv)

    connection_widget = DatabaseConnectionWidget(
        DatabaseConnectionManager())
    connection_widget.add_database_dialog(
        DatabaseConnectDialogDemo())
    connection_widget.show()
    sys.exit(app.exec_())
