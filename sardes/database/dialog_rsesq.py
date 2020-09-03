# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QSpinBox)

# ---- Local imports
from sardes.api.database_dialog import DatabaseConnectDialogBase
from sardes.config.locale import _
from sardes.database.accessors import DatabaseAccessorRSESQ


class DatabaseConnectDialogRSESQ(DatabaseConnectDialogBase):
    """
    Sardes database dialog class.

    This is the concrete class that provides a gui for the RSESQ PostgreSQL
    database accessor.
    """
    # The concrete database accessor class this dialog
    # is providing an interface to.
    __DatabaseAccessor__ = DatabaseAccessorRSESQ
    __database_type_name__ = 'RSESQ PostgreSQL'

    def __init__(self):
        super().__init__()

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

        self.add_widget(QLabel(_("Database :")), 0, 0)
        self.add_widget(self.dbname_lineedit, 0, 1, 1, 3)
        self.add_widget(QLabel(_("Username :")), 1, 0)
        self.add_widget(self.user_lineedit, 1, 1, 1, 3)
        self.add_widget(QLabel(_("Hostname :")), 2, 0)
        self.add_widget(self.host_lineedit, 2, 1)
        self.add_widget(QLabel(_("Port :")), 2, 2)
        self.add_widget(self.port_spinbox, 2, 3, Qt.AlignRight)
        self.add_widget(QLabel(_("Password :")), 3, 0)
        self.add_widget(self.password_lineedit, 3, 1, 1, 3)
        self.add_widget(QLabel(_("Encoding :")), 4, 0, Qt.AlignLeft)
        self.add_layout(encoding_layout, 4, 1)
        self.add_stretch(1)

    def set_database_kargs(self, kargs):
        if 'database' in kargs:
            self.dbname_lineedit.setText(kargs['database'])
        if 'username' in kargs:
            self.user_lineedit.setText(kargs['username'])
        if 'hostname' in kargs:
            self.host_lineedit.setText(kargs['hostname'])
        if 'port' in kargs:
            self.port_spinbox.setValue(int(kargs['port']))
        if 'password' in kargs:
            self.password_lineedit.setText(kargs['password'])
        if 'client_encoding' in kargs:
            self.encoding_lineedit.setText(kargs['client_encoding'])

    def get_database_kargs(self):
        """
        Return a dict that must match the constructor kargs signature of the
        database accessor class for which this dialog is providing an
        an interface to.
        """
        return {'database': self.dbname_lineedit.text(),
                'username': self.user_lineedit.text(),
                'hostname': self.host_lineedit.text(),
                'port': self.port_spinbox.value(),
                'password': self.password_lineedit.text(),
                'client_encoding': self.encoding_lineedit.text()}
