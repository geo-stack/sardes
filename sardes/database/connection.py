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
import psycopg2
from qtpy.QtCore import QObject, Qt, QThread, Signal, Slot
from qtpy.QtWidgets import (QApplication, QAbstractButton, QDialog,
                            QDialogButtonBox, QFormLayout, QGroupBox,
                            QLineEdit, QPushButton, QVBoxLayout)

# ---- Local imports
from sardes.config.database import get_dbconfig, set_dbconfig
from sardes.config.gui import RED
from sardes.widgets.statusbar import ProcessStatusBar


class DBConnWorker(QObject):
    """
    A simple worker to create a new database session without blocking the gui.
    """
    sig_conn_finished = Signal(object, object)

    def __init__(self, parent=None):
        super(DBConnWorker, self).__init__(parent)
        self.is_connecting = False
        self.database = ""
        self.user = ""
        self.password = ""
        self.host = ""

    def connect_to_bd(self):
        """Try to establish a connection with the database"""
        self.is_connecting = True
        try:
            conn = psycopg2.connect(
                database=self.database, user=self.user,
                host=self.host, password=self.password)
        except (psycopg2.Error) as e:
            conn = None
            error = e
        else:
            error = None
        self.is_connecting = False
        self.sig_conn_finished.emit(conn, error)


class BDConnManager(QDialog):
    """
    A dialog window to manage the connection to the database.
    """
    sig_connected = Signal(object)
    sig_disconnected = Signal()
    sig_connection_changed = Signal(bool)

    def __init__(self):
        super(BDConnManager, self).__init__()
        self.setWindowTitle('Database connection manager')
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setModal(True)

        self.conn = None
        self.setup()
        self._update_gui_from_config()

        self.db_conn_worker = DBConnWorker()
        self.db_conn_thread = QThread()
        self.db_conn_worker.moveToThread(self.db_conn_thread)
        self.db_conn_worker.sig_conn_finished.connect(self._handle_db_conn)
        self.db_conn_thread.started.connect(self.db_conn_worker.connect_to_bd)

        self.sig_connected.connect(
            lambda: self.sig_connection_changed.emit(self.is_connected()))
        self.sig_disconnected.connect(
            lambda: self.sig_connection_changed.emit(self.is_connected()))

    def setup(self):
        """
        Setup the dialog with the provided settings.
        """
        self.status_bar = ProcessStatusBar()
        self.status_bar.hide()

        # Setup the input data fields.
        self.dbname_lineedit = QLineEdit()
        self.host_lineedit = QLineEdit()
        self.user_lineedit = QLineEdit()
        self.password_lineedit = QLineEdit()
        self.password_lineedit.setEchoMode(QLineEdit.Password)

        self.form_groupbox = QGroupBox()
        self.form_groupbox.setAutoFillBackground(True)
        palette = QApplication.instance().palette()
        palette.setColor(self.form_groupbox.backgroundRole(),
                         palette.light().color())
        self.form_groupbox.setPalette(palette)

        form_layout = QFormLayout(self.form_groupbox)
        form_layout.addRow("Database :", self.dbname_lineedit)
        form_layout.addRow("Username :", self.user_lineedit)
        form_layout.addRow("Hostname :", self.host_lineedit)
        form_layout.addRow("Password :", self.password_lineedit)

        # Setup the dialog button box.
        self.connect_button = QPushButton('Connect')
        self.reset_button = QPushButton('Reset')
        self.ok_button = QPushButton('Ok')

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

    def is_connected(self):
        """Return whether a connection to a database is currently active."""
        return self.conn is not None

    def _update_gui(self):
        """
        Update the visibility and state of the gui based on the connection
        status with the database.
        """
        self.reset_button.setEnabled(
            self.conn is None and not self.db_conn_worker.is_connecting)
        self.form_groupbox.setEnabled(
            self.conn is None and not self.db_conn_worker.is_connecting)
        self.ok_button.setEnabled(not self.db_conn_worker.is_connecting)
        self.connect_button.setEnabled(not self.db_conn_worker.is_connecting)
        self.connect_button.setText(
            'Connect' if self.conn is None else 'Disconnect')

    def _update_gui_from_config(self):
        """
        Fetch the database connection parameters from the config and
        use them to setup the gui.

        This method is used during the setup of this dialog and when the user
        click on the 'reset' button.
        """
        dbconfig = get_dbconfig()
        self.dbname_lineedit.setText(dbconfig.get('database', ''))
        self.host_lineedit.setText(dbconfig.get('host', ''))
        self.user_lineedit.setText(dbconfig.get('user', ''))
        self.password_lineedit.setText(dbconfig.get('password', ''))

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
            if self.conn is None:
                self.connect()
            else:
                self.disconnect()

    @Slot(object, object)
    def _handle_db_conn(self, conn, error):
        """
        Handle when the database connection worker sucessfully or failed to
        create a new connection with the database.
        """
        self.db_conn_thread.quit()
        self.conn = conn
        if conn is None:
            if error:
                message = ('<font color="{}">{}:</font>'
                           ' {}'.format(RED, type(error).__name__, error))
            else:
                message = ("The connection to database <i>{}</i>"
                           " failed.".format(self.dbname_lineedit.text()))
            self.status_bar.show_fail_icon(message)
            self.sig_disconnected.emit()
        else:
            message = ("Connected to database "
                       "<i>{}</i>.".format(self.dbname_lineedit.text()))
            self.status_bar.show_sucess_icon(message)
            self.sig_connected.emit(self.conn)
        self._update_gui()

    def accept(self):
        """
        Accept user inputs, save them in the configuration file and
        close the dialog window.
        """
        set_dbconfig(database=self.dbname_lineedit.text(),
                     user=self.user_lineedit.text(),
                     host=self.host_lineedit.text(),
                     password=self.password_lineedit.text())
        self.close()

    def disconnect(self):
        """
        Close the connection with the database.
        """
        if self.conn is not None:
            self.conn.close()
            self.conn = None
            self.status_bar.hide()
            self._update_gui()
            self.sig_disconnected.emit()

    def connect(self):
        """
        Try to connect to the database using the connection parameters
        provided by the user in the gui.
        """
        self.db_conn_worker.database = self.dbname_lineedit.text()
        self.db_conn_worker.user = self.user_lineedit.text()
        self.db_conn_worker.password = self.password_lineedit.text()
        self.db_conn_worker.host = self.host_lineedit.text()
        self.db_conn_thread.start()
        self.db_conn_worker.is_connecting = True

        self._update_gui()
        self.status_bar.show()
        self.status_bar.set_label(
            "Connecting to database <i>{}</i>...".format(
                self.dbname_lineedit.text()))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    dialog = BDConnManager()
    dialog.show()
    sys.exit(app.exec_())
