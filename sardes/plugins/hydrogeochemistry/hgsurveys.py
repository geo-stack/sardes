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


class HGSurveyImportManager(QObject):
    def __init__(self):
        super().__init__()
        self.plugin = None
        self.table_models_manager = None

        self.import_dialog = HGSurveyImportDialog()
        self.import_dialog.sig_import_request.connect(
            self._handle_import_request)
        self.import_dialog.sig_continue_import.connect(
            self._import_hg_surveys)

        self.show_import_dialog_btn = create_toolbutton(
            parent=None,
            triggered=self.import_dialog.show,
            text=_("Import HG Surveys"),
            tip=_("Import HG surveys from an Excel Workbook."),
            icon='import_geochemistry'
            )

    def install_manager(self, plugin: Hydrogeochemistry):
        """Install this manager in the hydrogeochemistry plugin."""
        self.plugin = plugin

        plugin._tables['table_hg_surveys'].add_toolbar_separator('upper')
        plugin._tables['table_hg_surveys'].add_toolbar_widget(
            self.show_import_dialog_btn, 'upper')

        filepath = plugin.get_option('imput_hgsurvey_xlsx_filepath', None)
        if filepath is not None and osp.exists(filepath):
            self.import_dialog.input_file_pathbox.set_path(filepath)

    def close_manager(self):
        """Close this manager."""
        self.plugin.set_option(
            'imput_hgsurvey_xlsx_filepath',
            self.import_dialog.input_file_pathbox.path()
            )
        self.import_dialog.close()

    def _get_unsaved_tabletitles(self) -> list(StandardSardesTableModel):
        """Return the list of table names that contain unsaved changes."""
        unsaved_models = []
        names = ['table_hg_surveys', 'table_purges', 'table_hg_param_values']
        for name in names:
            model = self.plugin.main.table_models_manager.get_table_model(name)
            if model.has_unsaved_data_edits():
                unsaved_models.append(model)
        return [model.title() for model in unsaved_models]

    def _handle_import_request(self):
        """Handle import HG surveys requests."""
        # Get the list of relevant HG table models with unsaved changes.
        unsaved_models = self._get_unsaved_tabletitles()
        if len(unsaved_models) == 0:
            self._import_hg_surveys()
            return

        # Display a message to warn the user that all unsaved changes
        # will be lost when importing the hg surveys.
        message = "<h3>Unsaved Changes</h3>"
        message += "<p>"
        if len(unsaved_models) == 1:
            message += _(
                "Table <i>{}</i> contains unsaved changes.")
        elif len(unsaved_models) == 2:
            message += _(
                "Tables <i>{}</i> and <i>{}</i> contain unsaved changes.")
        elif len(unsaved_models) == 3:
            message += _(
                "Tables <i>{}</i>, <i>{}</i>, and <i>{}</i> contain "
                "unsaved changes.")
        message += "</p><p>"
        message += _("All unsaved changes will be lost. Do you want "
                     "to continue?")
        message += "</p>"

        self.import_dialog.show_unsaved_changes_dialog(
            message.format(*unsaved_models)
            )

    def _import_hg_surveys(self):
        """
        Import HG surveys from an XLSX file and add them to the database.
        """
        self.import_dialog.start_importing()
        imported_surveys_data = read_hgsurvey_data(
            self.import_dialog.input_file_pathbox.path()
            )
        self.plugin.main.db_connection_manager.add_hg_survey_data(
            imported_surveys_data,
            callback=self._handle_import_hg_surveys_results
            )

    def _handle_import_hg_surveys_results(self, response):
        """
        Handle the check foreign constraints results.
        """
        # Display the import error message to the user.
        if isinstance(response, ImportHGSurveysError):
            message = _(
                """
                <h3>Import Error</h3>
                <p>{}</p>
                <p>
                  Please resolve this problem in your Excel workbook
                  and try importing your data again.
                </p>
                """
                ).format(response.message)
            self.import_dialog.show_import_error_message(message)
            self.import_dialog.stop_importing(
                _("Failed to import HG surveys into the database."),
                success=False)
        else:
            self.import_dialog.stop_importing(response, success=True)


class HGSurveyImportDialog(UserMessageDialogBase):
    """
    A dialog window to import hg surveys from an Excel Workbook.
    """
    sig_closed = Signal()
    sig_import_request = Signal(bool)
    sig_continue_import = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_('Import HG Surveys'))
        self.setWindowIcon(get_icon('master'))
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
            tip=_("Select an xlsx files containing the hg survey data "
                  "to import in the database."),
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
            _("Select a valid hg survey input file :"))

        self.central_layout.addWidget(self.input_file_label)
        self.central_layout.addWidget(self.input_file_pathbox)
        self.central_layout.addWidget(self.status_bar)
        self.central_layout.addStretch(1)

        # Setup the unsaved warning message dialog.
        self.cancel_btn = self.create_button(
            _('Cancel'), enabled=True, default=False, visible=False,
            triggered=lambda: self._handle_cancel_import()
            )
        self.continue_btn = self.create_button(
            _('Continue'), enabled=True, default=False, visible=False,
            triggered=lambda: self._handle_continue_import()
            )
        self.unsaved_changes_dialog = self.create_msg_dialog(
            std_icon_name='SP_MessageBoxWarning',
            buttons=[self.continue_btn, self.cancel_btn]
            )
        self.add_msg_dialog(self.unsaved_changes_dialog)

        # Setup the import error dialog.
        self.ok_err_btn = self.create_button(
            _('Ok'), enabled=True, default=False, visible=False,
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

    def show_unsaved_changes_dialog(self, message: str):
        """
        Show a message to warn the user that there are unsaved changes in
        some tables that will be lost after importing hg survey data.
        """
        self.show_message_dialog(
            self.unsaved_changes_dialog, message, beep=True)

    def start_importing(self):
        """
        Start the publishing of the piezometric network.
        """
        self._import_in_progress = True
        self.input_file_label.setEnabled(False)
        self.input_file_pathbox.setEnabled(False)
        self.button_box.setEnabled(False)
        self.status_bar.show(_("Importing HG survey data..."))

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
    def _handle_continue_import(self):
        """
        Handle when the user has chosen to continue the import process
        in the "unsaved table changes" dialog.
        """
        self.close_message_dialogs()

        # This is required to avoid a glitch in the GUI.
        for i in range(5):
            QApplication.processEvents()

        self.sig_continue_import.emit()

    def _handle_cancel_import(self):
        """
        Handle when the user has chosen to cancel the import process
        in the "unsaved table changes" dialog.
        """
        self.close_message_dialogs()

    def _handle_xlsxfile_selected(self, path):
        """Handle when a new hg survey input xlsx file is selected."""
        self.import_btn.setEnabled(osp.exists(path) and osp.isfile(path))


def read_hgsurvey_data(filename: str) -> dict(dict):
    """
    Read HG survey data from a XLSX file.
    """
    wb = openpyxl.load_workbook(filename, data_only=True)
    sheet_names = wb.sheetnames

    all_surveys_data = {}
    for sheet_name in sheet_names:
        sheet = wb[sheet_name]

        hg_surveys_data = {
            'obs_well_id': sheet['C2'].value,
            'hg_survey_datetime': sheet['C3'].value,
            'hg_survey_operator': sheet['C4'].value,
            'survey_note': sheet['B7'].value,
            'hg_survey_depth': sheet['D25'].value,
            'hg_sampling_method_name': sheet['D26'].value,
            'sample_filtered': sheet['D27'].value,
            }

        purges_data = []
        for row in range(11, 21):
            if sheet[f'D{row}'].value is None:
                break
            purges_data.append({
                'purge_sequence_no': sheet[f'B{row}'].value,
                'purge_seq_start': sheet[f'C{row}'].value,
                'purge_seq_end': sheet[f'D{row}'].value,
                'purge_outflow': sheet[f'F{row}'].value,
                'pumping_depth': sheet[f'H{row}'].value,
                'pump_type_name': sheet['D24'].value,
                'water_level_drawdown': sheet[f'I{row}'].value
                })

        hg_param_values_data = []
        for row in range(31, 41):
            if sheet[f'B{row}'].value is None:
                continue

            new_param_data = {
                'hg_param_name': sheet[f'B{row}'].value,
                'hg_param_value': sheet[f'D{row}'].value,
                'meas_units_abb': sheet[f'E{row}'].value
                }
            for key, val in new_param_data.items():
                new_param_data[key] = str(val) if val is not None else None
            hg_param_values_data.append(new_param_data)

        all_surveys_data[sheet_name] = {
            'hg_surveys_data': hg_surveys_data,
            'purges_data': purges_data,
            'hg_param_values_data': hg_param_values_data
            }

    return all_surveys_data


def format_hg_survey_imported_data(
        imported_survey_name: str,
        imported_survey_data: dict,
        hg_surveys_data: pd.DataFrame,
        stations_data: pd.DataFrame,
        hg_sampling_methods_data: pd.DataFrame
        ) -> dict:
    """
    Format and sanitize HG survey data imported from a XLSX file.
    """
    new_hg_survey = {}

    # --- Get and check sampling_feature_uuid
    obs_well_id = imported_survey_data['obs_well_id']
    if obs_well_id is None:
        error_message = _(
            "No <i>observation well ID</i> is provided for survey <i>{}</i>."
            ).format(imported_survey_name)
        raise ImportHGSurveysError(error_message, code=101)
    else:
        try:
            sampling_feature_uuid = stations_data[
                stations_data['obs_well_id'] == obs_well_id
                ].iloc[0].name
        except IndexError:
            error_message = _(
                "The <i>observation well ID</i> provided for survey <i>{}</i> "
                "does not exist in the database."
                ).format(imported_survey_name)
            raise ImportHGSurveysError(error_message, code=102)
    new_hg_survey['sampling_feature_uuid'] = sampling_feature_uuid

    # --- Get and check hg_survey_datetime
    hg_survey_datetime = imported_survey_data['hg_survey_datetime']
    if not isinstance(hg_survey_datetime, datetime.datetime):
        error_message = _(
            "The <i>date-time</i> value provided for survey <i>{}</i> "
            "is not valid."
            ).format(imported_survey_name)
        raise ImportHGSurveysError(error_message, code=103)
    new_hg_survey['hg_survey_datetime'] = hg_survey_datetime

    # --- Check for duplicates
    dups = hg_surveys_data[
        (hg_surveys_data['sampling_feature_uuid'] == sampling_feature_uuid) &
        (hg_surveys_data['hg_survey_datetime'] == hg_survey_datetime)
        ]
    if len(dups) > 0:
        error_message = _(
            "A survey already exists in the database for the <i>observation "
            "well</i> and <i>date-time</i> provided for survey <i>{}</i>."
            ).format(imported_survey_name)
        raise ImportHGSurveysError(error_message, code=104)

    # --- Get and check hg_survey_depth
    hg_survey_depth = imported_survey_data['hg_survey_depth']
    if hg_survey_depth is not None:
        try:
            hg_survey_depth = float(hg_survey_depth)
        except ValueError:
            error_message = _(
                "The <i>survey depth</i> provided for survey <i>{}</i> "
                "is not valid."
                ).format(imported_survey_name)
            raise ImportHGSurveysError(error_message, code=105)
    new_hg_survey['hg_survey_depth'] = hg_survey_depth

    # --- Get and check hg_sampling_method_id
    hg_sampling_method_name = imported_survey_data[
        'hg_sampling_method_name']
    if hg_sampling_method_name is None:
        hg_sampling_method_id = None
    else:
        try:
            hg_sampling_method_id = hg_sampling_methods_data[
                hg_sampling_methods_data['hg_sampling_method_name'] ==
                hg_sampling_method_name
                ].iloc[0].name
        except IndexError:
            error_message = _(
                "The <i>sampling method</i> provided for survey <i>{}</i> "
                "is not valid."
                ).format(imported_survey_name)
            raise ImportHGSurveysError(error_message, code=106)
    new_hg_survey['hg_sampling_method_id'] = hg_sampling_method_id

    # --- Get and check sample_filtered
    sample_filtered = imported_survey_data['sample_filtered']
    if sample_filtered is not None:
        if sample_filtered not in (0, 1):
            error_message = _(
                "In survey <i>{}</i>, the filtered value must be either "
                "0 or 1."
                )
            raise ImportHGSurveysError(error_message, code=107)
    new_hg_survey['sample_filtered'] = sample_filtered

    new_hg_survey['hg_survey_operator'] = (
        imported_survey_data['hg_survey_operator'])
    new_hg_survey['survey_note'] = (
        imported_survey_data['survey_note'])

    return new_hg_survey


def format_purge_imported_data(
        imported_survey_name: str,
        imported_purge_data: dict,
        pump_type_data: pd.DataFrame
        ) -> dict:
    """
    Format and sanitize purge data imported from a XLSX file.
    """
    prev_seq_end = None
    new_purges = []
    for i, purge_seq_data in enumerate(imported_purge_data):
        new_purge = {
            'hg_survey_id': imported_survey_name,
            'purge_sequence_no': i + 1
            }

        purge_seq_start = purge_seq_data['purge_seq_start']
        if not isinstance(purge_seq_start, datetime.datetime):
            error_message = _(
                """
                For survey <i>{}</i>, the start date-time of purge
                sequence #{} is not valid.
                """
                ).format(imported_survey_name, i)
            raise ImportHGSurveysError(error_message, code=201)
        new_purge['purge_seq_start'] = purge_seq_start

        # Check that the start of the current sequence happens after
        # the end of the last sequence.
        if prev_seq_end is not None and prev_seq_end > purge_seq_start:
            error_message = _(
                """
                For survey <i>{}</i>, the start date-time of purge
                sequence #{} is less than the end-time of the previous
                sequence.
                """
                ).format(imported_survey_name, i)
            raise ImportHGSurveysError(error_message, code=202)

        purge_seq_end = purge_seq_data['purge_seq_end']
        if not isinstance(purge_seq_end, datetime.datetime):
            error_message = _(
                """
                In survey <i>{}</i>, the end date-time of purge
                sequence #{} is not valid.
                """
                ).format(imported_survey_name, i)
            raise ImportHGSurveysError(error_message, code=203)
        new_purge['purge_seq_end'] = purge_seq_end
        prev_seq_end = purge_seq_end

        if purge_seq_end <= purge_seq_start:
            error_message = _(
                """
                In survey <i>{}</i>, the end date-time of purge
                sequence #{} must be greater than its start date-time.
                """
                ).format(imported_survey_name, i)
            raise ImportHGSurveysError(error_message, code=204)

        # --- Get and check pump_type_id
        pump_type_name = purge_seq_data['pump_type_name']
        try:
            pump_type_id = pump_type_data[
                pump_type_data['pump_type_name'] == pump_type_name
                ].iloc[0].name
        except (IndexError, AssertionError):
            error_message = _(
                "The <i>pump type</i> provided for survey <i>{}</i> "
                "does not exist in the database."
                ).format(imported_survey_name)
            raise ImportHGSurveysError(error_message, code=205)
        new_purge['pump_type_id'] = pump_type_id

        # --- Get and check purge_outflow
        try:
            purge_outflow = abs(float(purge_seq_data['purge_outflow']))
        except (TypeError, ValueError):
            error_message = _(
                """
                The purge outflow provided in survey <i>{}</i>
                is not valid."
                """
                ).format(imported_survey_name)
            raise ImportHGSurveysError(error_message, code=206)
        new_purge['purge_outflow'] = purge_outflow

        pumping_depth = purge_seq_data['pumping_depth']
        if pumping_depth is not None:
            try:
                pumping_depth = float(pumping_depth)
            except ValueError:
                error_message = _(
                    """
                    The pumping depth provided in survey <i>{}</i>
                    is not valid.
                    """
                    ).format(imported_survey_name)
                raise ImportHGSurveysError(error_message, code=207)
        new_purge['pumping_depth'] = pumping_depth

        water_level_drawdown = purge_seq_data['water_level_drawdown']
        if water_level_drawdown is not None:
            try:
                water_level_drawdown = float(water_level_drawdown)
            except ValueError:
                error_message = _(
                    """
                    The water level drawdown provided in survey <i>{}</i>
                    is not valid.
                    """
                    ).format(imported_survey_name)
                raise ImportHGSurveysError(error_message, code=208)
        new_purge['water_level_drawdown'] = water_level_drawdown

        new_purges.append(new_purge)

    return new_purges


def format_params_data_imported_data(
        imported_survey_name: str,
        imported_param_data: dict,
        hg_params_data: pd.DataFrame,
        measurement_units_data: pd.DataFrame
        ) -> dict:
    """
    Format and sanitize in-situ parameters data imported from a XLSX file.
    """
    new_param_values = []
    for new_param_data in imported_param_data:
        new_param_value = {
            'hg_survey_id': imported_survey_name
            }

        # --- Get and check hg_param_name
        param_name = new_param_data['hg_param_name']
        if param_name is None or param_name == '':
            error_message = _(
                """
                In survey <i>{}</i>, one of the in-situ parameter
                has en empty name.
                """
                ).format(imported_survey_name)
            raise ImportHGSurveysError(error_message, code=301)

        for index, row in hg_params_data.iterrows():
            regex = row.hg_param_regex
            if regex is None or '':
                continue
            if re.match(regex, param_name, flags=re.IGNORECASE) is not None:
                hg_param_id = index
                break
        else:
            error_message = _(
                """
                In survey <i>{}</i>, there is no HG parameter in the
                database that matches the in-situ parameter
                named <i>{}</i>.
                """
                ).format(imported_survey_name, param_name)
            raise ImportHGSurveysError(error_message, code=302)
        new_param_value['hg_param_id'] = hg_param_id

        # --- Get and check meas_units_id
        meas_units_abb = new_param_data['meas_units_abb']
        try:
            meas_units_id = measurement_units_data[
                measurement_units_data['meas_units_abb'] == meas_units_abb
                ].iloc[0].name
        except IndexError:
            error_message = _(
                """
                In survey <i>{}</i>, the measurement units provided
                for the parameter <i>{}</i> is not valid.
                """
                ).format(imported_survey_name, param_name)
            raise ImportHGSurveysError(error_message, code=303)
        new_param_value['meas_units_id'] = meas_units_id

        # --- Get and check hg_param_value.
        hg_param_value = new_param_data['hg_param_value']
        try:
            assert hg_param_value is not None
            float(str(hg_param_value).replace('<', '').replace('>', ''))
        except (AssertionError, ValueError):
            error_message = _(
                """
                In survey <i>{}</i>, the value provided
                for the parameter <i>{}</i> is not valid.
                """
                )
            raise ImportHGSurveysError(error_message, code=304)
        new_param_value['hg_param_value'] = str(hg_param_value)

        new_param_values.append(new_param_value)

    return new_param_values


if __name__ == '__main__':
    import sys
    from qtpy.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dialog = HGSurveyImportDialog()
    dialog.show()
    sys.exit(app.exec_())
