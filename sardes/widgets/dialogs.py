# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------
from __future__ import annotations
from typing import TYPE_CHECKING, Callable

# ---- Standard library imports
import os
import os.path as osp
import sys
import datetime
import tempfile

# ---- Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QGridLayout, QLabel, QPushButton,
    QTextEdit, QWidget, QStackedWidget, QVBoxLayout)

# ---- Local imports
from sardes import __namever__, __appname__, __issues_url__, get_versions
from sardes.config.icons import (
    get_icon, get_standard_icon, get_standard_iconsize)
from sardes.config.locale import _
from sardes.config.main import TEMP_DIR
from sardes.widgets.statusbar import ProcessStatusBar
from sardes.utils.qthelpers import get_default_contents_margins


EXCEPT_DIALOG_MSG_CANVAS = (
    "### {}\n<".format(_("Description")) +
    _("Please provide a step-by-step description of what "
      "led to the problem here.") +
    ">\n\n### {}\n".format(_("System Info")) +
    "{namever}\n" +
    "Python {python_ver} {bitness}-bit\n" +
    "Qt {qt_ver}\n" +
    "{qt_api} {qt_api_ver}\n" +
    "{os_name} {os_ver}" +
    "\n\n### {}\n".format(_("Traceback")) +
    "```python-traceback\n{log_msg}```"
    )


class ExceptDialog(QDialog):
    """
    A dialog to report internal errors encountered by the application during
    execution.
    """

    def __init__(self, log_msg=None, detailed_log=None):
        super().__init__()
        self.setWindowTitle(_("{} Internal Error").format(__appname__))
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setWindowIcon(get_icon('master'))

        self.detailed_log = detailed_log
        self.log_datetime = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

        self.logmsg_textedit = QTextEdit()
        self.logmsg_textedit.setReadOnly(True)
        self.logmsg_textedit.setMinimumWidth(400)
        self.set_log_message(log_msg)

        icon = get_standard_icon('SP_MessageBoxCritical')
        iconsize = get_standard_iconsize('messagebox')
        info_icon = QLabel()
        info_icon.setScaledContents(False)
        info_icon.setPixmap(icon.pixmap(iconsize))

        # Setup dialog buttons.
        self.ok_btn = QPushButton(_('OK'))
        self.ok_btn.setDefault(True)
        self.ok_btn.clicked.connect(self.close)

        self.copy_btn = QPushButton(_('Copy'))
        self.copy_btn.setDefault(False)
        self.copy_btn.clicked.connect(self.copy)

        button_box = QDialogButtonBox()
        button_box.addButton(self.copy_btn, button_box.AcceptRole)
        button_box.addButton(self.ok_btn, button_box.ActionRole)

        if self.detailed_log is not None and len(self.detailed_log):
            # Setup the dialog button box.
            self.showlog_btn = QPushButton(_('Detailed Log'))
            self.showlog_btn.setDefault(False)
            self.showlog_btn.clicked.connect(self.show_detailed_log)
            button_box.addButton(self.showlog_btn, button_box.ResetRole)

        # Setup dialog main message.
        message = _(
            '<b>{0} has encountered an internal problem.</b>'
            '<p>We are sorry, but {1} encountered an internal error that '
            'might preventing it from running correctly. You might want to '
            'save your work and restart {1} if possible.</p>'
            '<p>Please report this error by copying the information below '
            'in our <a href="{2}">issues tracker</a> and by providing '
            'a step-by-step description of what led to the problem.</p>'
            ).format(__namever__, __appname__, __issues_url__)
        if self.detailed_log is not None and len(self.detailed_log):
            message += _(
                '<p>If possible, please also attach to your report the '
                'detailed log file accessible by clicking on the '
                '<i>Detailed Log</i> button.</p>'
                )
        msg_labl = QLabel(message)
        msg_labl.setWordWrap(True)
        msg_labl.setOpenExternalLinks(True)

        # Setup layout.
        left_side_layout = QGridLayout()
        left_side_layout.setContentsMargins(0, 0, 10, 0)
        left_side_layout.addWidget(info_icon)
        left_side_layout.setRowStretch(1, 1)

        right_side_layout = QGridLayout()
        right_side_layout.setContentsMargins(0, 0, 0, 0)
        right_side_layout.addWidget(msg_labl)
        right_side_layout.addWidget(self.logmsg_textedit)

        main_layout = QGridLayout(self)
        main_layout.addLayout(left_side_layout, 0, 0)
        main_layout.addLayout(right_side_layout, 0, 1)
        main_layout.addWidget(button_box, 1, 0, 1, 2)

    def set_log_message(self, log_msg):
        """
        Set the log message related to the encountered error.
        """
        self.logmsg_textedit.setText(
            self._render_error_infotext(log_msg or ''))

    def get_error_infotext(self):
        """
        Return the text containing the information relevant to the
        encountered error that can be copy-pasted directly
        in an issue on GitHub.
        """
        return self.logmsg_textedit.toPlainText()

    def _render_error_infotext(self, log_msg):
        """
        Render the information relevant to the encountered error in a format
        that can be copy-pasted directly in an issue on GitHub.
        """
        versions = get_versions()
        formatted_msg = EXCEPT_DIALOG_MSG_CANVAS.format(
            namever=__namever__,
            python_ver=versions['python'],
            bitness=versions['bitness'],
            qt_ver=versions['qt'],
            qt_api=versions['qt_api'],
            qt_api_ver=versions['qt_api_ver'],
            os_name=versions['system'],
            os_ver=versions['release'],
            log_msg=log_msg)
        return formatted_msg

    def show_detailed_log(self):
        """
        Open the detailed log file in an external application that is
        chosen by the OS.
        """
        name = 'SardesLog_{}.txt'.format(self.log_datetime)
        temp_path = tempfile.mkdtemp(dir=TEMP_DIR)
        temp_filename = osp.join(temp_path, name)
        with open(temp_filename, 'w') as txtfile:
            txtfile.write(self.detailed_log)
        os.startfile(temp_filename)

    def copy(self):
        """
        Copy the issue on the clipboard.
        """
        QApplication.clipboard().clear()
        QApplication.clipboard().setText(self.get_error_infotext())


class UserMessageDialogBase(QDialog):
    """
    Basic functionalies to implement a dialog window that provide
    the capability to show messages to the user.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.__setup__()

    def __setup__(self):
        """Setup the dialog with the provided settings."""

        self._buttons = []

        self.button_box = QDialogButtonBox()
        self.button_box.layout().addStretch(1)
        self.button_box.layout().setContentsMargins(
            *get_default_contents_margins())

        # Setup the main widget.
        self.central_widget = QWidget()
        self.central_layout = QVBoxLayout(self.central_widget)
        self.central_layout.addStretch(1)

        # Setup the stacked widget.
        self._dialogs = []

        self.stackwidget = QStackedWidget()
        self.stackwidget.addWidget(self.central_widget)
        self.stackwidget.setMinimumHeight(100)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.stackwidget)
        main_layout.addWidget(self.button_box)
        main_layout.setSizeConstraint(main_layout.SetFixedSize)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

    # ---- Helpers Methods
    def create_button(self, text: str, enabled: bool = True,
                      triggered: Callable = None, default: bool = False
                      ) -> QPushButton:
        """Create a pushbutton to add to the button box."""
        button = QPushButton(text)
        button.setDefault(default)
        button.setAutoDefault(False)
        if triggered is not None:
            button.clicked.connect(triggered)
        button.setEnabled(enabled)
        return button

    def add_button(self, button):
        """Add a new pushbutton to the button box."""
        self._buttons.append(button)
        self.button_box.layout().addWidget(button)

    def create_msg_dialog(self, std_icon_name: str,
                          buttons: list[QPushButton]
                          ) -> ProcessStatusBar:
        """Create a new message dialog."""
        dialog = ProcessStatusBar(
            spacing=10,
            icon_valign='top',
            vsize_policy='expanding',
            text_valign='top',
            iconsize=get_standard_iconsize('messagebox'),
            contents_margin=get_default_contents_margins())
        dialog.set_icon('failed', get_standard_icon(std_icon_name))
        dialog.setAutoFillBackground(True)
        dialog._buttons = buttons

        palette = QApplication.instance().palette()
        palette.setColor(dialog.backgroundRole(), palette.light().color())
        dialog.setPalette(palette)

        # Hide the buttons of the dialogs.
        for btn in buttons:
            btn.setVisible(False)

        return dialog

    def add_msg_dialog(self, dialog: ProcessStatusBar):
        """Add a new message dialog to the stack widget."""
        self._dialogs.append(dialog)
        self.stackwidget.addWidget(dialog)
        for button in dialog._buttons:
            self.add_button(button)

    # ---- Public Interface
    def show_message_dialog(
            self, dialog: ProcessStatusBar, message: str, beep: bool = True):
        """Show to the user the specified dialog with the provided message."""
        self.show()
        for btn in self._buttons:
            btn.setVisible(btn in dialog._buttons)
        dialog.show_fail_icon(message)
        self.stackwidget.setCurrentWidget(dialog)
        if beep is True:
            QApplication.beep()

    def close_message_dialogs(self):
        """Close all message dialogs and show the main interface."""
        for btn in self._buttons:
            btn.setVisible(True)
        for dialog in self._dialogs:
            for btn in dialog._buttons:
                btn.setVisible(False)
        self.stackwidget.setCurrentWidget(self.central_widget)

    def show(self):
        """Overide Qt method."""
        super().show()
        self.activateWindow()
        self.raise_()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    dialog = ExceptDialog("Some Traceback\n")
    dialog.show()
    sys.exit(app.exec_())
