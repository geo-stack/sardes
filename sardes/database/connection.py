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
from qtpy.QtCore import QObject, QSize, Qt, QThread, Signal, Slot
from qtpy.QtWidgets import (QApplication, QAbstractButton, QDialog,
                            QDialogButtonBox, QFormLayout, QGridLayout,
                            QGroupBox, QLabel, QLineEdit, QPushButton,
                            QVBoxLayout, QWidget)

# ---- Local imports
from sardes.config.database import get_dbconfig, set_dbconfig
from sardes.config.icons import get_icon
from sardes.config.gui import RED
from sardes.utils.qthelpers import create_waitspinner


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


class DBConnectionStatusBar(QWidget):
    """
    A status bar that shows the connection status to the database.
    """

    def __init__(self, parent=None):
        super(DBConnectionStatusBar, self).__init__(parent)

        self._label = QLabel()
        self._label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._label.setWordWrap(True)
        self._label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self._spinner = create_waitspinner(size=24)

        self._failed_icon = QLabel()
        self._failed_icon.setPixmap(get_icon('failed').pixmap(QSize(24, 24)))
        self._failed_icon.hide()

        self._success_icon = QLabel()
        self._success_icon.setPixmap(get_icon('succes').pixmap(QSize(24, 24)))
        self._success_icon.hide()

        layout = QGridLayout(self)

        alignment = Qt.AlignLeft | Qt.AlignVCenter
        layout.addWidget(self._spinner, 1, 0, alignment)
        layout.addWidget(self._failed_icon, 1, 0, alignment)
        layout.addWidget(self._success_icon, 1, 0, alignment)
        layout.setColumnMinimumWidth(1, 5)
        layout.addWidget(self._label, 1, 2)

        layout.setRowStretch(0, 100)
        layout.setRowStretch(3, 100)
        layout.setColumnStretch(2, 100)

    def set_label(self, text):
        """Set the text that is displayed next to the spinner."""
        self._label.setText(text)

    def show_fail_icon(self):
        """Stop and hide the spinner and show a failed icon instead."""
        self._spinner.hide()
        self._spinner.stop()
        self._success_icon.hide()
        self._failed_icon.show()

    def show_sucess_icon(self):
        """Stop and hide the spinner and show a success icon instead."""
        self._spinner.hide()
        self._spinner.stop()
        self._failed_icon.hide()
        self._success_icon.show()

    def show(self):
        """Extend Qt method to start the waiting spinner."""
        self._spinner.show()
        self._failed_icon.hide()
        self._success_icon.hide()
        super().show()
        self._spinner.start()

    def hide(self):
        """Extend Qt hide to stop waiting spinner."""
        super().hide()
        self._spinner.stop()


class BDConnManager(QDialog):
    """
    A dialog window to manage the connection to the database.
    """

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

    def setup(self):
        """
        Setup the dialog with the provided settings.
        """
        self.status_bar = DBConnectionStatusBar()
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
            self.status_bar.show_fail_icon()
            if error:
                self.status_bar.set_label(
                    '<font color="{}">{}:</font>'
                    ' {}'.format(RED, type(error).__name__, error))
            else:
                self.status_bar.set_label(
                    "The connection to database <i>{}</i> failed.".format(
                        self.dbname_lineedit.text()))
        else:
            self.status_bar.show_sucess_icon()
            self.status_bar.set_label(
                "Connected to database <i>{}</i>.".format(
                    self.dbname_lineedit.text()))
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
