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
from qtpy.QtCore import QObject, Qt, QThread, Signal, Slot
from qtpy.QtWidgets import (
    QApplication, QAbstractButton, QComboBox, QDialog, QDialogButtonBox,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QSpinBox)
from sqlalchemy import create_engine
from sqlalchemy.exc import DBAPIError

# ---- Local imports
from sardes.config.database import get_dbconfig, set_dbconfig
from sardes.config.gui import RED
from sardes.widgets.statusbar import ProcessStatusBar


# https://docs.python.org/3.7/library/codecs.html#standard-encodings
CHAR_ENCODINGS = [
    'ascii', 'big5', 'big5hkscs', 'cp037', 'cp273', 'cp424',  'cp437', 'cp500',
    'cp720', 'cp737', 'cp775', 'cp850', 'cp852', 'cp855', 'cp856', 'cp857',
    'cp858', 'cp860', 'cp861', 'cp862', 'cp863', 'cp864', 'cp865', 'cp866',
    'cp869', 'cp874', 'cp875', 'cp932', 'cp949', 'cp950', 'cp1006', 'cp1026',
    'cp1125', 'cp1140', 'cp1250', 'cp1251', 'cp1252', 'cp1253', 'cp1254',
    'cp1255', 'cp1256', 'cp1257', 'cp1258', 'cp65001', 'euc_jp',
    'euc_jis_2004', 'euc_jisx0213', 'euc_kr', 'gb2312', 'gbk', 'gb18030', 'hz',
    'iso2022_jp', 'iso2022_jp_1', 'iso2022_jp_2', 'iso2022_jp_2004',
    'iso2022_jp_3', 'iso2022_jp_ext', 'iso2022_kr', 'latin_1', 'iso8859_2',
    'iso8859_3', 'iso8859_4', 'iso8859_5', 'iso8859_6', 'iso8859_7',
    'iso8859_8', 'iso8859_9', 'iso8859_10', 'iso8859_11', 'iso8859_13',
    'iso8859_14', 'iso8859_15', 'iso8859_16', 'johab', 'koi8_r', 'koi8_t',
    'koi8_u', 'kz1048', 'mac_cyrillic', 'mac_greek', 'mac_iceland',
    'mac_latin2', 'mac_roman', 'mac_turkish', 'ptcp154', 'shift_jis',
    'shift_jis_2004', 'shift_jisx0213', 'utf_32', 'utf_32_be', 'utf_32_le',
    'utf_16', 'utf_16_be', 'utf_16_le', 'utf_7', 'utf_8', 'utf_8_sig']


class DatabaseConnWorker(QObject):
    """
    A simple worker to create a new database session without blocking the gui.
    """
    sig_conn_finished = Signal(object, object)

    def __init__(self, parent=None):
        super(DatabaseConnWorker, self).__init__(parent)
        self.is_connecting = False
        self.database = ""
        self.user = ""
        self.password = ""
        self.host = ""
        self.port = 5432

    def connect_to_bd(self):
        """Try to establish a connection with the database"""
        self.is_connecting = True
        db_engine = create_engine(
            "postgresql://{}:{}@{}:{}/{}".format(self.user,
                                                 self.password,
                                                 self.host,
                                                 self.port,
                                                 self.database),
            client_encoding='utf8')
        try:
            conn = db_engine.connect()
        except DBAPIError as e:
            conn = None
            error = e
        else:
            error = None
        self.is_connecting = False
        self.sig_conn_finished.emit(conn, error)


class DatabaseConnWidget(QDialog):
    """
    A dialog window to manage the connection to the database.
    """
    sig_connected = Signal(object)
    sig_disconnected = Signal()
    sig_connection_changed = Signal(bool)

    def __init__(self, parent=None):
        super(DatabaseConnWidget, self).__init__(parent)
        self.setWindowTitle('Database connection manager')
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setModal(True)

        self.conn = None
        self.setup()
        self._update_gui_from_config()

        self.db_conn_worker = DatabaseConnWorker()
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

        # Setup the database connection parameter input fields.
        self.dbname_lineedit = QLineEdit()
        self.host_lineedit = QLineEdit()
        self.port_spinbox = QSpinBox()
        self.port_spinbox.setRange(0, 65535)
        self.port_spinbox.setValue(5432)
        self.user_lineedit = QLineEdit()
        self.password_lineedit = QLineEdit()
        self.password_lineedit.setEchoMode(QLineEdit.Password)

        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(CHAR_ENCODINGS)
        encoding_layout = QHBoxLayout()
        encoding_layout.addWidget(self.encoding_combo)
        encoding_layout.addStretch(1)

        self.form_groupbox = QGroupBox()
        self.form_groupbox.setAutoFillBackground(True)
        palette = QApplication.instance().palette()
        palette.setColor(self.form_groupbox.backgroundRole(),
                         palette.light().color())
        self.form_groupbox.setPalette(palette)

        form_layout = QGridLayout(self.form_groupbox)
        form_layout.addWidget(QLabel("Database :"), 0, 0)
        form_layout.addWidget(self.dbname_lineedit, 0, 1, 1, 3)
        form_layout.addWidget(QLabel("Username :"), 1, 0)
        form_layout.addWidget(self.user_lineedit, 1, 1, 1, 3)
        form_layout.addWidget(QLabel("Hostname :"), 2, 0)
        form_layout.addWidget(self.host_lineedit, 2, 1)
        form_layout.addWidget(QLabel("Port :"), 2, 2)
        form_layout.addWidget(self.port_spinbox, 2, 3, Qt.AlignRight)
        form_layout.addWidget(QLabel("Password :"), 3, 0)
        form_layout.addWidget(self.password_lineedit, 3, 1, 1, 3)
        form_layout.addWidget(QLabel("Encoding :"), 4, 0, Qt.AlignLeft)
        form_layout.addLayout(encoding_layout, 4, 1)
        form_layout.setRowStretch(form_layout.rowCount(), 1)

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
        self.dbname_lineedit.setText(dbconfig['database'])
        self.host_lineedit.setText(dbconfig['host'])
        self.port_spinbox.setValue(dbconfig['port'])
        self.user_lineedit.setText(dbconfig['user'])
        self.password_lineedit.setText(dbconfig['password'])
        self.encoding_combo.setCurrentIndex(
            self.encoding_combo.findText(dbconfig['encoding']))

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
                     port=self.port_spinbox.value(),
                     password=self.password_lineedit.text(),
                     encoding=self.encoding_combo.currentText())
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
    dialog = DatabaseConnWidget()
    dialog.show()
    sys.exit(app.exec_())
