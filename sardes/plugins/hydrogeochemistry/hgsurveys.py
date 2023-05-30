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

# ---- Third party imports
import pandas as pd
import openpyxl
from qtpy.QtCore import Qt, Signal, QObject
from qtpy.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QPushButton, QVBoxLayout,
    QStackedWidget, QWidget, QApplication)

# ---- Local imports
from sardes.config.icons import (
    get_icon, get_standard_iconsize, get_standard_icon)
from sardes.config.locale import _
from sardes.widgets.statusbar import ProcessStatusBar
from sardes.utils.qthelpers import format_tooltip
from sardes.utils.qthelpers import create_toolbutton
from sardes.widgets.path import PathBoxWidget
from sardes.utils.qthelpers import get_default_contents_margins


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
            icon='image'
            )

    def install_manager(self, plugin: Hydrogeochemistry):
        """Install this manager in the hydrogeochemistry plugin."""
        self.plugin = plugin

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
        # unsaved_models = self._get_unsaved_tabletitles()
        unsaved_models = ['HG Surveys', 'Purges', 'HG Params Value']
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
        print("import_hg_surveys")
        pass


class HGSurveyImportDialog(QDialog):
    """
    A dialog window to import hg surveys from an Excel Workbook.
    """
    sig_closed = Signal()
    sig_import_request = Signal(bool)
    sig_continue_import = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_('Import HG Surveys'))
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setWindowIcon(get_icon('master'))
        self.setModal(False)
        self.setWindowModality(Qt.ApplicationModal)

        self._import_in_progress = False

        self.__setup__()

    def __setup__(self):
        """Setup the dialog with the provided settings."""
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
        self.import_btn = QPushButton(_('Import'))
        self.import_btn.setDefault(True)
        self.import_btn.clicked.connect(
            lambda: self.sig_import_request.emit(True))
        self.import_btn.setEnabled(False)

        self.close_btn = QPushButton(_('Close'))
        self.close_btn.setDefault(False)
        self.close_btn.setAutoDefault(False)
        self.close_btn.clicked.connect(self.close)

        self.cancel_btn = QPushButton(_('Cancel'))
        self.cancel_btn.setDefault(False)
        self.cancel_btn.setAutoDefault(False)
        self.cancel_btn.clicked.connect(
            lambda: self._handle_cancel_import())
        self.cancel_btn.setVisible(False)

        self.continue_btn = QPushButton(_('Continue'))
        self.continue_btn.setDefault(False)
        self.continue_btn.setAutoDefault(False)
        self.continue_btn.clicked.connect(
            lambda: self._handle_continue_import())
        self.continue_btn.setVisible(False)

        self.button_box = QDialogButtonBox()
        self.button_box.layout().addStretch(1)
        self.button_box.layout().addWidget(self.import_btn)
        self.button_box.layout().addWidget(self.close_btn)
        self.button_box.layout().addWidget(self.cancel_btn)
        self.button_box.layout().addWidget(self.continue_btn)
        self.button_box.layout().setContentsMargins(
            *get_default_contents_margins())

        # Setup the main widget.
        self.input_file_label = QLabel(
            _("Select a valid hg survey input file :"))

        base_widget = QWidget()
        base_layout = QVBoxLayout(base_widget)
        base_layout.addWidget(self.input_file_label)
        base_layout.addWidget(self.input_file_pathbox)
        base_layout.addWidget(self.status_bar)
        base_layout.addStretch(1)

        # Setup the unsaved changes warning message.
        self.unsaved_changes_dialog = ProcessStatusBar(
            spacing=10,
            icon_valign='top',
            iconsize=get_standard_iconsize('messagebox'),
            contents_margin=get_default_contents_margins())
        self.unsaved_changes_dialog.set_icon(
            'failed', get_standard_icon('SP_MessageBoxWarning'))

        self.unsaved_changes_dialog.setAutoFillBackground(True)
        palette = QApplication.instance().palette()
        palette.setColor(
            self.unsaved_changes_dialog.backgroundRole(),
            palette.light().color())
        self.unsaved_changes_dialog.setPalette(palette)

        # Setup the stacked widget.
        self.stackwidget = QStackedWidget()
        self.stackwidget.addWidget(base_widget)
        self.stackwidget.addWidget(self.unsaved_changes_dialog)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.stackwidget)
        main_layout.addWidget(self.button_box)
        main_layout.setSizeConstraint(main_layout.SetFixedSize)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

    # ---- Public Interface
    def show_unsaved_changes_dialog(self, message: str):
        """
        Show a message to warn the user that there are unsaved changes in
        some tables that will be lost after importing hg survey data.
        """
        self.import_btn.setVisible(False)
        self.close_btn.setVisible(False)
        self.cancel_btn.setVisible(True)
        self.continue_btn.setVisible(True)
        self.unsaved_changes_dialog.show_fail_icon(message)
        self.stackwidget.setCurrentWidget(self.unsaved_changes_dialog)
        QApplication.beep()

    def close_unsaved_changes_dialog(self):
        """
        Close the unsaved changes dialog.
        """
        self.import_btn.setVisible(True)
        self.close_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        self.continue_btn.setVisible(False)
        self.stackwidget.setCurrentIndex(0)

    def start_importing(self):
        """
        Start the publishing of the piezometric network.
        """
        self._import_in_progress = True
        self.input_file_label.setEnabled(False)
        self.input_file_pathbox.setEnabled(False)
        self.button_box.setEnabled(False)
        self.status_bar.show(_("Reading HG survey data..."))

    def stop_importing(self):
        """
        Start the publishing of the piezometric network.
        """
        self._import_in_progress = False
        self.input_file_pathbox.setEnabled(True)
        self.button_box.setEnabled(True)
        self.status_bar.show(_("Reading HG survey data..."))

    # ---- Handlers
    def _handle_continue_import(self):
        """
        Handle when the user has chosen to continue the import process
        in the "unsaved table changes" dialog.
        """
        self.close_unsaved_changes_dialog()
        self.sig_continue_import.emit()

    def _handle_cancel_import(self):
        """
        Handle when the user has chosen to cancel the import process
        in the "unsaved table changes" dialog.
        """
        self.close_unsaved_changes_dialog()

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
            'pump_type_name': sheet['D24'].value,
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
                'water_level_drawdown': sheet[f'I{row}'].value
                })

        hg_param_values_data = []
        for row in range(31, 41):
            if sheet[f'B{row}'].value is None:
                break

            hg_param_values_data.append({
                'hg_param_name': sheet[f'B{row}'].value,
                'hg_param_value': sheet[f'D{row}'].value,
                'meas_units_abb': sheet[f'E{row}'].value,
                })

        all_surveys_data[sheet_name] = {
            'hg_surveys_data': hg_surveys_data,
            'purges_data': purges_data,
            'hg_param_values_data': hg_param_values_data
            }

    return all_surveys_data


def format_hg_survey_imported_data(
        imported_survey_data: dict, hg_surveys_data: pd.DataFrame,
        stations_data: pd.DataFrame, hg_sampling_methods_data: pd.DataFrame
        ) -> dict:
    """
    Format and sanitize HG survey data imported from a XLSX file.
    """
    new_hg_survey = {}

    # --- sampling_feature_uuid
    obs_well_id = imported_survey_data['obs_well_id']
    if obs_well_id is None:
        return 'obs_well_id cannot be None bitch!'
    else:
        try:
            new_hg_survey['sampling_feature_uuid'] = stations_data[
                stations_data['obs_well_id'] == obs_well_id
                ].iloc[0]
        except IndexError:
            return 'This monitoring station does not exists bitch'

    # --- hg_survey_datetime
    hg_survey_datetime = imported_survey_data['hg_survey_datetime']
    if hg_survey_datetime is None:
        return 'hg_survey_datetime cannot be None bitch!'
    elif not isinstance(hg_survey_datetime, datetime.datetime):
        return 'This is not a valid date sucker!'
    new_hg_survey['hg_survey_datetime'] = hg_survey_datetime

    # --- hg_survey_depth
    hg_survey_depth = imported_survey_data['hg_survey_depth']
    if hg_survey_depth is not None:
        try:
            hg_survey_depth = float(hg_survey_depth)
        except ValueError:
            return 'Wrong survey depth value cunt'
    new_hg_survey['hg_survey_depth'] = hg_survey_depth

    # --- hg_sampling_method_id
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
            return 'This sampling method does not exists fucker!'
    new_hg_survey['hg_sampling_method_id'] = hg_sampling_method_id

    # --- sample_filtered
    sample_filtered = imported_survey_data['sample_filtered']
    if sample_filtered is not None:
        if sample_filtered not in (0, 1):
            return 'sample_filtered must be either 0 or 1 prick!'
    new_hg_survey['sample_filtered'] = sample_filtered

    new_hg_survey['hg_survey_operator'] = (
        imported_survey_data['hg_survey_operator'])
    new_hg_survey['survey_note'] = (
        imported_survey_data['survey_note'])

    return new_hg_survey


if __name__ == '__main__':
    import sys
    from qtpy.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dialog = HGSurveyImportDialog()
    dialog.show()
    sys.exit(app.exec_())
