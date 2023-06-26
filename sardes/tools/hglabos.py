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
from sardes.config.main import CONF
from sardes.config.icons import get_icon
from sardes.config.locale import _
from sardes.widgets.statusbar import ProcessStatusBar
from sardes.widgets.dialogs import UserMessageDialogBase
from sardes.utils.qthelpers import format_tooltip
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
        import_dialog = HGLabReportImportDialog(
            win_title=_("Import HG Lab Report"),
            parent=self.table
            )
        import_dialog.sig_import_request.connect(self._import_hg_surveys)

        filepath = CONF.get(
            self.table.table_name(),
            'path_import_hglab_reports_tool',
            None)
        if filepath is not None and osp.exists(filepath):
            import_dialog.input_file_pathbox.set_path(filepath)

        return import_dialog

    def __on_close__(self):
        if self.toolwidget() is not None:
            CONF.set(
                self.table.table_name(),
                'path_import_hglab_reports_tool',
                self.toolwidget().input_file_pathbox.path()
                )

    # ---- Handlers
    def _import_hg_surveys(self):
        """
        Import HG surveys from an XLSX file and add them to the database.
        """
        self.toolwidget().start_importing(_("Importing HG lab report..."))
        hglab_data = read_hglab_data(
            self.toolwidget().input_file_pathbox.path())
        try:
            libraries = self.table.model().libraries
            fmt_hglab_data = format_hglab_data(
                hglab_data,
                observation_wells_data=libraries['observation_wells_data'],
                hg_surveys_data=libraries['hg_surveys'],
                hg_params_data=libraries['hg_params'],
                measurement_units_data=libraries['measurement_units'],
                hg_labs_data=libraries['hg_labs']
                )
        except ImportHGSurveysError as e:
            self._handle_import_error(e)
        else:
            self.table.tableview._append_row(fmt_hglab_data)
            msg = _("Lab report data was successfully imported.")
            self.toolwidget().stop_importing(msg, success=True)

    def _handle_import_error(self, error):
        """
        Handle the check foreign constraints results.
        """
        message = _(
            """
            <h3>Import Error</h3>
            <p>{}</p>
            <p>
              Please resolve this problem in your lab report
              and try importing your data again.
            </p>
            """
            ).format(error.message)
        self.toolwidget().show_import_error_message(message)
        self.toolwidget().stop_importing(
            _("Failed to import lab report data."),
            success=False)


class HGLabReportImportDialog(UserMessageDialogBase):
    """
    A dialog window to import hg surveys from an Excel Workbook.
    """
    sig_closed = Signal()
    sig_import_request = Signal(str)

    def __init__(self, win_title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(win_title)
        self.setWindowIcon(get_icon('import_lab_report'))
        self.setModal(False)

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
            triggered=lambda: self.sig_import_request.emit(
                self.input_file_pathbox.path())
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

    def start_importing(self, text: str):
        """
        Start the publishing of the piezometric network.
        """
        self._import_in_progress = True
        self.input_file_label.setEnabled(False)
        self.input_file_pathbox.setEnabled(False)
        self.button_box.setEnabled(False)
        self.status_bar.show(text)

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


def read_hglab_data(filename: str) -> dict[list[dict]]:
    """
    Read HG lab report data from a XLSX file.
    """
    wb = openpyxl.load_workbook(filename, data_only=True)
    sheet_names = wb.sheetnames

    all_lab_reports = {}
    for sheet_name in sheet_names:
        new_lab_report = []

        sheet = wb[sheet_name]

        lab_report_date = sheet['C2'].value
        lab_code = sheet['C3'].value

        row = 6
        while True:
            if sheet[f'B{row}'].value is None:
                break

            new_lab_report.append({
                'lab_report_date': lab_report_date,
                'lab_code': lab_code,
                'obs_well_id': sheet[f'B{row}'].value,
                'hg_survey_datetime': sheet[f'C{row}'].value,
                'lab_sample_id': sheet[f'D{row}'].value,
                'hg_param_expr': sheet[f'E{row}'].value,
                'hg_param_value': sheet[f'F{row}'].value,
                'lim_detection': sheet[f'G{row}'].value,
                'meas_units_abb': sheet[f'H{row}'].value,
                'method': sheet[f'I{row}'].value,
                'notes': sheet[f'J{row}'].value,
                })
            row += 1

        if len(new_lab_report) > 0:
            all_lab_reports[sheet_name] = new_lab_report

    return all_lab_reports


def format_hglab_data(
        all_lab_reports: dict,
        observation_wells_data: pd.DataFrame,
        hg_surveys_data: pd.DataFrame,
        hg_params_data: pd.DataFrame,
        measurement_units_data: pd.DataFrame,
        hg_labs_data: pd.DataFrame,
        ) -> list(dict):
    """
    Format HG lab report data that were read from a XLSX file.
    """
    fmt_hglab_data = []
    for hglab_name, hglab_data in all_lab_reports.items():
        for i, param_data in enumerate(hglab_data):
            new_hg_param = {}

            # --- Check lab report date and labo code.
            lab_report_date = param_data['lab_report_date']
            if (lab_report_date is not None and
                    not isinstance(lab_report_date, datetime.datetime)):
                error_message = _(
                    """
                    The date of the lab report <i>{}</i> is not valid.
                    """
                    ).format(hglab_name)
            new_hg_param['lab_report_date'] = lab_report_date

            lab_code = param_data['lab_code']
            if lab_code is not None:
                try:
                    lab_id = hg_labs_data[
                        hg_labs_data['lab_code'] == lab_code
                        ].iloc[0].name
                except IndexError:
                    error_message = _(
                        """
                        The lab code of the lab report <i>{}</i>
                        is not valid.
                        """
                        ).format(hglab_name, i + 1)
                    raise ImportHGSurveysError(error_message, code=401)
                new_hg_param['lab_id'] = lab_id
            else:
                new_hg_param['lab_id'] = None

            # ---- Get sampling_feature_uuid
            obs_well_id = param_data['obs_well_id']
            try:
                assert obs_well_id is not None
                sampling_feature_uuid = observation_wells_data[
                    observation_wells_data['obs_well_id'] == obs_well_id
                    ].iloc[0].name
            except (IndexError, AssertionError):
                error_message = _(
                    """
                    In the lab report <i>{}</i>, the <i>observation well ID</i>
                    provided for the parameter #{} is not valid.
                    """
                    ).format(hglab_name, i + 1)
                raise ImportHGSurveysError(error_message, code=401)

            # --- Get and check hg_survey_datetime
            hg_survey_datetime = param_data['hg_survey_datetime']
            if not isinstance(hg_survey_datetime, datetime.datetime):
                error_message = _(
                    """
                    In the lab report <i>{}</i>, the <i>survey date-time</i>
                    provided for the parameter #{} is not valid.
                    """
                    ).format(hglab_name, i + 1)
                raise ImportHGSurveysError(error_message, code=402)

            # --- Get the hg_survey_id.
            try:
                hg_survey_id = (
                    hg_surveys_data[
                        (hg_surveys_data['sampling_feature_uuid'] ==
                         sampling_feature_uuid) &
                        (hg_surveys_data['hg_survey_datetime'] ==
                         hg_survey_datetime)]
                    ).iloc[0].name
            except IndexError:
                error_message = _(
                    """
                    In the lab report <i>{}</i>, no HG survey was found
                    in the database for well ID <i>{}</i> and date-time
                    <i>{}</i>.
                    """
                    ).format(hglab_name,
                             obs_well_id,
                             hg_survey_datetime.strftime("%Y-%m-%d %H:%M"))
            new_hg_param['hg_survey_id'] = hg_survey_id

            # --- Get and check meas_units_id
            meas_units_abb = param_data['meas_units_abb']
            try:
                meas_units_id = measurement_units_data[
                    measurement_units_data['meas_units_abb'] == meas_units_abb
                    ].iloc[0].name
            except IndexError:
                error_message = _(
                    """
                    In the lab report <i>{}</i>, the measurement units
                    provided for the parameter #{} is not valid.
                    """
                    ).format(hglab_name, i + 1)
                raise ImportHGSurveysError(error_message, code=303)
            new_hg_param['meas_units_id'] = meas_units_id

            # --- Get and check hg_param_value.
            hg_param_value = param_data['hg_param_value']
            try:
                assert hg_param_value is not None
                float(str(hg_param_value).replace('<', '').replace('>', ''))
            except (AssertionError, ValueError):
                error_message = _(
                    """
                    In the lab report <i>{}</i>, the value
                    provided for the parameter #{} is not valid.
                    """
                    ).format(hglab_name, i + 1)
                raise ImportHGSurveysError(error_message, code=304)
            new_hg_param['hg_param_value'] = str(hg_param_value)

            # --- Check lim_detection
            lim_detection = param_data['lim_detection']
            if lim_detection is not None:
                try:
                    lim_detection = float(lim_detection)
                except ValueError:
                    error_message = _(
                        """
                        In the lab report <i>{}</i>, the limit detection
                        provided for the parameter #{} is not valid.
                        """
                        ).format(hglab_name, i + 1)
                    raise ImportHGSurveysError(error_message, code=304)
                new_hg_param['lim_detection'] = lim_detection
            else:
                new_hg_param['lim_detection'] = None

            # --- Get and check hg_param_id
            param_expr = param_data['hg_param_expr']
            if param_expr is None or param_expr == '':
                error_message = _(
                    """
                    In the lab report <i>{}</i>, the name
                    provided for the parameter #{} is not valid.
                    """
                    ).format(hglab_name, i + 1)
                raise ImportHGSurveysError(error_message, code=301)

            for index, row in hg_params_data.iterrows():
                regex = row.hg_param_regex
                if regex is None or '':
                    continue
                if re.match(regex, param_expr,
                            flags=re.IGNORECASE) is not None:
                    hg_param_id = index
                    break
            else:
                error_message = _(
                    """
                    In the lab report <i>{}</i>, there is no HG parameter
                    in the database that matches the name
                    provided for the parameter #{}.
                    """
                    ).format(hglab_name, i + 1)
                raise ImportHGSurveysError(error_message, code=302)

            new_hg_param['hg_param_id'] = hg_param_id

            new_hg_param['lab_sample_id'] = param_data['lab_sample_id']
            new_hg_param['method'] = param_data['method']
            new_hg_param['lab_sample_id'] = param_data['lab_sample_id']
            new_hg_param['notes'] = param_data['notes']

            fmt_hglab_data.append(new_hg_param)

    return fmt_hglab_data
