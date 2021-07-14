# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard library imports
import sys
import os.path as osp
import datetime

# ---- Third party imports
from qtpy.QtCore import Qt, QObject, Signal
from qtpy.QtGui import QTextCursor
from qtpy.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QGridLayout, QPushButton,
    QTextEdit, QFileDialog, QMessageBox)

# ---- Local imports
from sardes.config.locale import _
from sardes.config.icons import get_icon
from sardes.config.ospath import (
    get_select_file_dialog_dir, set_select_file_dialog_dir)


class StandardStreamEmitter(QObject):
    """
    A Qt object to intercept and emit the input and output of the
    Python interpreter.

    https://docs.python.org/3/library/sys.html#sys.stdout
    https://docs.python.org/3/library/sys.html#sys.stderr
    """
    sig_new_text = Signal(str)

    def write(self, text):
        sys.__stdout__.write(text)
        self.sig_new_text.emit(str(text))


