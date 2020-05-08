# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Third party imports
from qtpy.QtWidgets import QHBoxLayout, QLabel, QLineEdit

# ---- Local imports
from sardes.api.database_dialog import DatabaseConnectDialogBase
from sardes.config.locale import _
from sardes.database.accessor_sardes_lite import DatabaseAccessorSardesLite
from sardes.widgets.path import PathBoxWidget


class DatabaseConnectDialogSardesLite(DatabaseConnectDialogBase):
    """
    Sardes database dialog class.

    This is the concrete class that provides a gui for the Sardes SQLite
    database accessor.
    """
    # The concrete database accessor class this dialog
    # is providing an interface to.
    __DatabaseAccessor__ = DatabaseAccessorSardesLite
    __database_type_name__ = 'Sardes SQLite'

    def __init__(self):
        super().__init__()

        self.dbname_widget = PathBoxWidget(
            path_type='getOpenFileName', filters='*.db')

        self.encoding_lineedit = QLineEdit()
        encoding_layout = QHBoxLayout()
        encoding_layout.addWidget(self.encoding_lineedit)
        encoding_layout.addStretch(1)

        self.add_widget(QLabel(_("Database :")), 0, 0)
        self.add_widget(self.dbname_widget, 0, 1)
        self.add_stretch(1)

    def set_database_kargs(self, kargs):
        if 'database' in kargs:
            self.dbname_widget.set_path(kargs['database'])

    def get_database_kargs(self):
        """
        Return a dict that must match the constructor kargs signature of the
        database accessor class for which this dialog is providing an
        an interface to.
        """
        return {'database': self.dbname_widget.path()}
