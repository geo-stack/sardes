# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Third party imports
from qtpy.QtCore import QSize, Qt
from qtpy.QtWidgets import QGridLayout, QLabel, QWidget

from sardes.config.icons import get_icon
from sardes.utils.qthelpers import create_waitspinner


class ProcessStatusBar(QWidget):
    """
    A status bar that shows the progression status and results of a process.
    """
    HIDDEN = 0
    IN_PROGRESS = 1
    PROCESS_SUCCEEDED = 2
    PROCESS_FAILED = 3

    def __init__(self, parent=None, orientation=Qt.Horizontal):
        super().__init__(parent)
        self._status = self.HIDDEN

        self._label = QLabel()
        if orientation == Qt.Horizontal:
            self._label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        else:
            self._label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
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
        layout.setContentsMargins(0, 0, 0, 0)

        alignment = Qt.AlignLeft | Qt.AlignVCenter
        layout.addWidget(self._spinner, 1, 1, alignment)
        layout.addWidget(self._failed_icon, 1, 1, alignment)
        layout.addWidget(self._success_icon, 1, 1, alignment)
        if orientation == Qt.Horizontal:
            layout.setColumnMinimumWidth(2, 5)
            layout.addWidget(self._label, 1, 3)
            layout.setRowStretch(0, 100)
            layout.setRowStretch(3, 100)
            layout.setColumnStretch(3, 100)
            layout.setSpacing(0)
        else:
            layout.addWidget(self._label, 2, 1)
            layout.setRowStretch(0, 100)
            layout.setRowStretch(4, 100)
            layout.setColumnStretch(0, 100)
            layout.setColumnStretch(2, 100)
            layout.setSpacing(5)

    @property
    def status(self):
        return self._status

    def set_label(self, text):
        """Set the text that is displayed next to the spinner."""
        self._label.setText(text)

    def show_fail_icon(self, message=None):
        """Stop and hide the spinner and show a failed icon instead."""
        self._status = self.PROCESS_FAILED
        self._spinner.hide()
        self._spinner.stop()
        self._success_icon.hide()
        self._failed_icon.show()
        if message is not None:
            self.set_label(message)

    def show_sucess_icon(self, message=None):
        """Stop and hide the spinner and show a success icon instead."""
        self._status = self.PROCESS_SUCCEEDED
        self._spinner.hide()
        self._spinner.stop()
        self._failed_icon.hide()
        self._success_icon.show()
        if message is not None:
            self.set_label(message)

    def show(self, message=None):
        """Extend Qt method to start the waiting spinner."""
        self._status = self.IN_PROGRESS
        self._spinner.show()
        self._failed_icon.hide()
        self._success_icon.hide()
        super().show()
        self._spinner.start()
        if message is not None:
            self.set_label(message)

    def hide(self):
        """Extend Qt hide to stop waiting spinner."""
        self._status = self.HIDDEN
        super().hide()
        self._spinner.stop()
