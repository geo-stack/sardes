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
import traceback

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


class StandardStreamConsole(QTextEdit):
    """
    A Qt text edit to hold and show the standard input and output of the
    Python interpreter.
    """

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)

    def write(self, text):
        self.moveCursor(QTextCursor.End)
        self.insertPlainText(text)


class SardesConsole(QDialog):
    """
    A console to hold, show and manage the standard input and ouput
    of the Python interpreter.
    """

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            self.windowFlags() &
            ~Qt.WindowContextHelpButtonHint |
            Qt.WindowMinMaxButtonsHint)
        self.setWindowIcon(get_icon('console'))
        self.setWindowTitle(_("Sardes Console"))
        self.setMinimumSize(700, 500)

        self.std_console = StandardStreamConsole()

        # Setup the dialog button box.
        self.saveas_btn = QPushButton(_('Save As'))
        self.saveas_btn.setDefault(False)
        self.saveas_btn.clicked.connect(lambda checked: self.save_as())

        self.close_btn = QPushButton(_('Close'))
        self.close_btn.setDefault(True)
        self.close_btn.clicked.connect(self.close)

        self.copy_btn = QPushButton(_('Copy'))
        self.copy_btn.setDefault(False)
        self.copy_btn.clicked.connect(self.copy_to_clipboard)

        button_box = QDialogButtonBox()
        button_box.addButton(self.close_btn, button_box.AcceptRole)
        button_box.addButton(self.saveas_btn, button_box.ActionRole)
        button_box.addButton(self.copy_btn, button_box.ActionRole)

        # self.setCentralWidget(self.std_console)
        layout = QGridLayout(self)
        layout.addWidget(self.std_console, 0, 0)
        layout.addWidget(button_box, 1, 0)

    def write(self, text):
        self.std_console.write(text)

    def plain_text(self):
        """
        Return the content of the console as plain text.
        """
        return self.std_console.toPlainText()

    def save_as(self, filename=None):
        """
        Save the content of the console to a text file.
        """
        if filename is None:
            now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = osp.join(
                get_select_file_dialog_dir(),
                'SardesLog_{}.txt'.format(now)
                )
        filename, filefilter = QFileDialog.getSaveFileName(
            self, _("Save File"), filename, '{} (*.txt)'.format(_("Text File"))
            )
        if filename:
            filename = osp.abspath(filename)
            set_select_file_dialog_dir(osp.dirname(filename))
            if not filename.endswith('.txt'):
                filename += '.txt'

            QApplication.setOverrideCursor(Qt.WaitCursor)
            QApplication.processEvents()
            try:
                with open(filename, 'w') as txtfile:
                    txtfile.write(self.plain_text())
            except PermissionError:
                QApplication.restoreOverrideCursor()
                QApplication.processEvents()
                QMessageBox.warning(
                    self,
                    _('File in Use'),
                    _("The save file operation cannot be completed because "
                      "the file is in use by another application or user."),
                    QMessageBox.Ok)
                self.save_as(filename)
            else:
                QApplication.restoreOverrideCursor()
                QApplication.processEvents()

    def copy_to_clipboard(self):
        """
        Copy the content of the console on the clipboard.
        """
        QApplication.clipboard().clear()
        QApplication.clipboard().setText(self.plain_text())

    def show(self):
        """
        Override Qt method.
        """
        if self.windowState() == Qt.WindowMinimized:
            self.setWindowState(Qt.WindowNoState)
        super().show()
        self.activateWindow()
        self.raise_()


if __name__ == '__main__':
    from sardes.utils.qthelpers import create_application
    app = create_application()

    console = SardesConsole()
    console.show()

    sys.exit(app.exec_())
