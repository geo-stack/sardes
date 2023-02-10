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
from qtpy.QtCore import QSize, Qt, Signal
from qtpy.QtWidgets import (QGridLayout, QLabel, QWidget, QPushButton,
                            QToolButton, QStyle, QFrame, QApplication,
                            QHBoxLayout)

from sardes.config.icons import get_icon
from sardes.utils.qthelpers import create_waitspinner


class MessageBoxWidget(QWidget):
    """
    A warning box that can be installed in a Sardes table widget.
    """
    sig_next_warning = Signal()
    sig_prev_warning = Signal()
    sig_closed = Signal()
    sig_button_clicked = Signal(object)

    def __init__(self, parent=None, color=None, icon=None):
        super().__init__(parent)
        self.buttons = []

        self._label = QLabel('')
        self._label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._label.setWordWrap(True)

        self._icon = QLabel()
        if icon is not None:
            icon_size = self.style().pixelMetric(QStyle.PM_ToolBarIconSize)
            self._icon.setPixmap(
                get_icon(icon).pixmap(QSize(icon_size, icon_size)))

        self._button_box = QHBoxLayout()
        self._button_box.setContentsMargins(0, 0, 0, 0)

        self._close_button = QToolButton()
        self._close_button.setAutoRaise(True)
        self._close_button.setIcon(get_icon('close'))
        icon_size = self._close_button.style().pixelMetric(
            QStyle.PM_TabCloseIndicatorHeight)
        self._close_button.setIconSize(QSize(icon_size, icon_size))
        self._close_button.clicked.connect(self.close)

        msgbox_frame = QFrame()
        msgbox_frame.setObjectName("msg_box_frame")
        msgbox_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        if color is not None:
            msgbox_frame.setStyleSheet(
                "QFrame#msg_box_frame {"
                "background-color: %s; "
                "}" % color)

        msgbox_frame_layout = QHBoxLayout(msgbox_frame)
        msgbox_frame_layout.setContentsMargins(3, 3, 3, 3)
        msgbox_frame_layout.addWidget(self._icon)
        msgbox_frame_layout.addWidget(self._label)
        msgbox_frame_layout.addSpacing(20)
        msgbox_frame_layout.addLayout(self._button_box)
        msgbox_frame_layout.addSpacing(20)
        msgbox_frame_layout.addWidget(self._close_button, Qt.AlignVCenter)
        msgbox_frame_layout.setStretch(1, 1)

        msg_box_layout = QGridLayout(self)
        msg_box_layout.setContentsMargins(0, 0, 0, 0)
        msg_box_layout.addWidget(msgbox_frame)

    def add_button(self, label, clicked_callback=None):
        new_button = QPushButton(label)
        new_button.setAutoDefault(False)
        new_button.setDefault(False)
        new_button.setFocusPolicy(Qt.TabFocus)
        if clicked_callback is not None:
            new_button.clicked.connect(clicked_callback)
        self.buttons.append(new_button)
        self._button_box.addWidget(new_button)
        return new_button

    def set_message(self, message):
        self._label.setText(message)

    def closeEvent(self, event):
        """Override Qt method to emit a signal when closing."""
        self.sig_closed.emit()
        super().closeEvent(event)


class ProcessStatusBar(QWidget):
    """
    A status bar that shows the progression status and results of a process.
    """
    HIDDEN = 0
    IN_PROGRESS = 1
    PROCESS_SUCCEEDED = 2
    PROCESS_FAILED = 3

    def __init__(self, parent=None, iconsize=24, ndots=11,
                 orientation=Qt.Horizontal, spacing=None, margin=0):
        super().__init__(parent)
        self._status = self.HIDDEN

        self._label = QLabel()
        if orientation == Qt.Horizontal:
            self._label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        else:
            self._label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self._label.setWordWrap(True)
        self._label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self._spinner = create_waitspinner(iconsize, ndots, self)

        self._failed_icon = QLabel()
        self._failed_icon.setPixmap(
            get_icon('failed').pixmap(QSize(iconsize, iconsize)))
        self._failed_icon.hide()

        self._success_icon = QLabel()
        self._success_icon.setPixmap(
            get_icon('succes').pixmap(QSize(iconsize, iconsize)))
        self._success_icon.hide()

        layout = QGridLayout(self)
        layout.setContentsMargins(margin, margin, margin, margin)

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
            layout.setSpacing(spacing or 0)
        else:
            layout.addWidget(self._label, 2, 1)
            layout.setRowStretch(0, 100)
            layout.setRowStretch(4, 100)
            layout.setColumnStretch(0, 100)
            layout.setColumnStretch(2, 100)
            layout.setSpacing(spacing or 5)

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


if __name__ == '__main__':
    app = QApplication(sys.argv)

    msgbox = MessageBoxWidget()
    msgbox.set_message("Some warning message.")
    msgbox.show()

    sys.exit(app.exec_())
