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
    QApplication, QAbstractButton, QDialog, QDialogButtonBox, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QSpinBox)

# ---- Local imports
from sardes.config.database import get_dbconfig, set_dbconfig
from sardes.config.gui import RED
from sardes.config.locale import _
from sardes.widgets.statusbar import ProcessStatusBar


class DatabaseConnectionWidget(QDialog):
    """
    A dialog window to manage the connection to the database.
    """

    def __init__(self, db_connection_manager=None, parent=None):
        super(DatabaseConnectionWidget, self).__init__(parent)
        self.setWindowTitle(_('Database connection manager'))
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setModal(True)

        self.setup()
        self._update_gui_from_config()
        self.set_database_connection_manager(db_connection_manager)

    def set_database_connection_manager(self, db_connection_manager):
        """
        Setup the database connection manager for this widget.
        """
        self.db_connection_manager = db_connection_manager
        if db_connection_manager is not None:
            self.db_connection_manager.sig_database_connected.connect(
                self._handle_database_connected)
            self.db_connection_manager.sig_database_disconnected.connect(
                self._handle_database_disconnected)

    def setup(self):
        """
        Setup the dialog with the provided settings.
        """
        self.status_bar = ProcessStatusBar()
        self.status_bar.hide()

        # Setup the database connection parameter input fields.
        self.dbname_lineedit = QLineEdit()
        self.host_lineedit = QLineEdit()
        self.port_spinbox = QSpinBox()
        self.port_spinbox.setRange(0, 65535)
        self.port_spinbox.setValue(5432)
        self.user_lineedit = QLineEdit()
        self.password_lineedit = QLineEdit()
        self.password_lineedit.setEchoMode(QLineEdit.Password)

        self.encoding_lineedit = QLineEdit()
        encoding_layout = QHBoxLayout()
        encoding_layout.addWidget(self.encoding_lineedit)
        encoding_layout.addStretch(1)

        self.form_groupbox = QGroupBox()
        self.form_groupbox.setAutoFillBackground(True)
        palette = QApplication.instance().palette()
        palette.setColor(self.form_groupbox.backgroundRole(),
                         palette.light().color())
        self.form_groupbox.setPalette(palette)

        form_layout = QGridLayout(self.form_groupbox)
        form_layout.addWidget(QLabel(_("Database :")), 0, 0)
        form_layout.addWidget(self.dbname_lineedit, 0, 1, 1, 3)
        form_layout.addWidget(QLabel(_("Username :")), 1, 0)
        form_layout.addWidget(self.user_lineedit, 1, 1, 1, 3)
        form_layout.addWidget(QLabel(_("Hostname :")), 2, 0)
        form_layout.addWidget(self.host_lineedit, 2, 1)
        form_layout.addWidget(QLabel(_("Port :")), 2, 2)
        form_layout.addWidget(self.port_spinbox, 2, 3, Qt.AlignRight)
        form_layout.addWidget(QLabel(_("Password :")), 3, 0)
        form_layout.addWidget(self.password_lineedit, 3, 1, 1, 3)
        form_layout.addWidget(QLabel(_("Encoding :")), 4, 0, Qt.AlignLeft)
        form_layout.addLayout(encoding_layout, 4, 1)
        form_layout.setRowStretch(form_layout.rowCount(), 1)

        # Setup the dialog button box.
        self.connect_button = QPushButton(_('Connect'))
        self.reset_button = QPushButton(_('Reset'))
        self.ok_button = QPushButton(_('Ok'))

        button_box = QDialogButtonBox()
        button_box.addButton(self.ok_button, QDialogButtonBox.AcceptRole)
        button_box.addButton(self.connect_button, QDialogButtonBox.ApplyRole)
        button_box.addButton(self.reset_button, QDialogButtonBox.ResetRole)
        button_box.layout().insertSpacing(1, 100)
        button_box.clicked.connect(self._handle_button_click_event)

        # Setup the main layout.
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.form_groupbox)
        main_layout.addWidget(self.status_bar)
        main_layout.addWidget(button_box)
        main_layout.setStretch(0, 1)
        main_layout.setSizeConstraint(main_layout.SetFixedSize)

    def _update_gui(self):
        """
        Update the visibility and state of the gui based on the connection
        status with the database.
        """
        is_connecting = self.db_connection_manager.is_connecting()
        is_connected = self.db_connection_manager.is_connected()
        self.reset_button.setEnabled(not is_connected and not is_connecting)
        self.form_groupbox.setEnabled(not is_connected and not is_connecting)
        self.ok_button.setEnabled(not is_connecting)
        self.connect_button.setEnabled(not is_connecting)
        self.connect_button.setText(
            _('Disconnect') if is_connected else _('Connect'))

    def _update_gui_from_config(self):
        """
        Fetch the database connection parameters from the config and
        use them to setup the gui.

        This method is used during the setup of this dialog and when the user
        click on the 'reset' button.
        """
        dbconfig = get_dbconfig()
        self.dbname_lineedit.setText(dbconfig['database'])
        self.host_lineedit.setText(dbconfig['host'])
        self.port_spinbox.setValue(dbconfig['port'])
        self.user_lineedit.setText(dbconfig['user'])
        self.password_lineedit.setText(dbconfig['password'])
        self.encoding_lineedit.setText(dbconfig['encoding'])

    # ---- Signal handlers
    @Slot(QAbstractButton)
    def _handle_button_click_event(self, button):
        """
        Handle when a button is clicked on the dialog button box.
        """
        if button == self.ok_button:
            self.accept()
        elif button == self.reset_button:
            self._update_gui_from_config()
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
                message = _("The connection to database <i>{}</i> "
                            "failed.").format(self.dbname_lineedit.text())
            self.status_bar.show_fail_icon(message)
        else:
            message = _("Connected to database <i>{}</i>.").format(
                self.dbname_lineedit.text())
            self.status_bar.show_sucess_icon(message)
        self._update_gui()

    @Slot()
    def _handle_database_disconnected(self):
        """
        Handle when the connection to the database was sucessfully closed.
        """
        self.status_bar.hide()
        self._update_gui()

    def accept(self):
        """
        Accept user inputs, save them in the configuration file and
        close the dialog window.
        """
        set_dbconfig(database=self.dbname_lineedit.text(),
                     user=self.user_lineedit.text(),
                     host=self.host_lineedit.text(),
                     port=self.port_spinbox.value(),
                     password=self.password_lineedit.text(),
                     encoding=self.encoding_lineedit.text())
        self.close()

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
            database=self.dbname_lineedit.text(),
            user=self.user_lineedit.text(),
            password=self.password_lineedit.text(),
            host=self.host_lineedit.text(),
            port=self.port_spinbox.value(),
            client_encoding=self.encoding_lineedit.text())
        self._update_gui()
        self.status_bar.show()
        self.status_bar.set_label(
            _("Connecting to database <i>{}</i>...").format(
                self.dbname_lineedit.text()))


if __name__ == '__main__':
    from sardes.database.manager import DatabaseConnectionManager
    app = QApplication(sys.argv)
    manager = DatabaseConnectionManager()
    dialog = DatabaseConnectionWidget(manager)
    dialog.show()
    sys.exit(app.exec_())
