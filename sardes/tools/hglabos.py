# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sardes.tables.models import StandardSardesTableModel
    from sardes.plugins.hydrogeochemistry.plugin import Hydrogeochemistry

# ---- Standard imports
import datetime
import os.path as osp
import re

# ---- Third party imports
import pandas as pd
import openpyxl
from qtpy.QtCore import Qt, Signal, QObject
from qtpy.QtWidgets import QLabel, QApplication

# ---- Local imports
from sardes.config.icons import get_icon
from sardes.config.locale import _
from sardes.widgets.statusbar import ProcessStatusBar
from sardes.widgets.dialogs import UserMessageDialogBase
from sardes.utils.qthelpers import format_tooltip
from sardes.utils.qthelpers import create_toolbutton
from sardes.widgets.path import PathBoxWidget
from sardes.database.accessors.accessor_errors import ImportHGSurveysError
from sardes.api.tools import SardesTool


class HGLaboImportTool(SardesTool):
    def __init__(self, table):
        super().__init__(
            table,
            name='import_hglabo_report_tool',
            text=_("Import HG Lab Report"),
            icon='import_lab_report',
            tip=_("Import HG data from an Excel lab report.")
            )

    # ---- SardesTool API
    def __update_toolwidget__(self, toolwidget):
        pass

    def __create_toolwidget__(self):
        return HGSurveyImportDialog(
            win_title=_("Import HG Lab Report"),
            parent=self.table
            )


class HGSurveyImportDialog(UserMessageDialogBase):
    """
    A dialog window to import hg surveys from an Excel Workbook.
    """
    sig_closed = Signal()
    sig_import_request = Signal(bool)
    sig_continue_import = Signal()

    def __init__(self, win_title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(win_title)
        self.setWindowIcon(get_icon('import_lab_report'))
        self.setModal(False)
        self.setWindowModality(Qt.ApplicationModal)

        self._import_in_progress = False

        # Setup the input file path widget.
        self.input_file_pathbox = PathBoxWidget(
            path_type='getOpenFileName',
            filters="Excel Workbook (*.xlsx)")
        self.input_file_pathbox.browse_btn.setText(_('Select...'))
        self.input_file_pathbox.browse_btn.setToolTip(format_tooltip(
            text=_("Select Import File"),
            tip=_("Select an xlsx file containing the formatted data "
                  "of a hydrogeochemical lab report."),
            shortcuts=None
            ))
        self.input_file_pathbox.path_lineedit.setMinimumWidth(300)
        self.input_file_pathbox.sig_path_changed.connect(
            self._handle_xlsxfile_selected)

        # Setup the status bar.
        self.status_bar = ProcessStatusBar()
        self.status_bar.hide()

        # Setup the dialog button box.
        self.import_btn = self.create_button(
            _('Import'), enabled=False, default=True,
            triggered=lambda: self.sig_import_request.emit(True)
            )
        self.close_btn = self.create_button(
            _('Close'), enabled=True, default=False,
            triggered=self.close
            )
        self.add_button(self.import_btn)
        self.add_button(self.close_btn)

        # Setup the main widget.
        self.input_file_label = QLabel(
            _("Select a valid HG lab report file :"))

        self.central_layout.addWidget(self.input_file_label)
        self.central_layout.addWidget(self.input_file_pathbox)
        self.central_layout.addWidget(self.status_bar)
        self.central_layout.addStretch(1)

        # Setup the import error dialog.
        self.ok_err_btn = self.create_button(
            _('Ok'), enabled=True, default=False,
            triggered=self.close_message_dialogs
            )
        self.import_error_dialog = self.create_msg_dialog(
            std_icon_name='SP_MessageBoxCritical',
            buttons=[self.ok_err_btn]
            )
        self.add_msg_dialog(self.import_error_dialog)

    # ---- Public Interface
    def show_import_error_message(self, message: str):
        """
        Show the message of an error that occured during the import process.
        """
        self.show_message_dialog(
            self.import_error_dialog, message, beep=True)

    def start_importing(self):
        """
        Start the publishing of the piezometric network.
        """
        self._import_in_progress = True
        self.input_file_label.setEnabled(False)
        self.input_file_pathbox.setEnabled(False)
        self.button_box.setEnabled(False)
        self.status_bar.show(_("Importing HG lab report..."))

    def stop_importing(self, message: str, success: bool):
        """
        Start the publishing of the piezometric network.
        """
        self.show()
        self._import_in_progress = False
        self.input_file_pathbox.setEnabled(True)
        self.button_box.setEnabled(True)
        if success is True:
            self.status_bar.show_sucess_icon(message)
        else:
            self.status_bar.show_fail_icon(message)

    # ---- Handlers
    def _handle_xlsxfile_selected(self, path):
        """Handle when a new hg lab report is selected."""
        self.import_btn.setEnabled(osp.exists(path) and osp.isfile(path))

