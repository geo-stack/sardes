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
from qtpy.QtWidgets import QLabel

# ---- Local imports
from sardes.api.database_dialog import DatabaseConnectDialogBase
from sardes.config.locale import _
from sardes.database.accessors import DatabaseAccessorDemo


class DatabaseConnectDialogDemo(DatabaseConnectDialogBase):
    """
    Sardes database dialog class.

    This is the concrete class that provides a gui for the Sardes database
    accessor test and debug class.
    """
    __DatabaseAccessor__ = DatabaseAccessorDemo
    __database_type_name__ = 'Sardes Demo'

    def __init__(self):
        super().__init__()

        message_label = QLabel(
            _("This is a demo mode to test Sardes without needing "
              "to connect to a database. "
              "Note that any changes made in demo mode will be lost when "
              "Sardes is restarted.\n\n"
              "Click 'Connect' to start testing Sardes in demo mode."))
        message_label.setWordWrap(True)
        self.add_widget(message_label, 0, 0, Qt.AlignCenter)
