# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports
import datetime
import os.path as osp

# ---- Third party imports
from appconfigs.base import get_home_dir
import hydsensread as hsr
import pandas as pd
from qtpy.QtCore import Qt, QSize, Slot, Signal
from qtpy.QtWidgets import (QApplication, QFileDialog, QTabWidget,
                            QDialog, QGridLayout, QLabel, QPushButton,
                            QDialogButtonBox, QVBoxLayout, QAbstractButton,
                            QFormLayout, QGroupBox)

# ---- Local imports
from sardes.config.main import CONF
from sardes.api.plugins import SardesPlugin
from sardes.api.tablemodels import SardesTableModel
from sardes.api.timeseries import DataType
from sardes.config.icons import get_icon
from sardes.config.locale import _
from sardes.utils.qthelpers import (
    create_mainwindow_toolbar, create_toolbutton)
from sardes.widgets.tableviews import NotEditableDelegate, SardesTableWidget


NOT_FOUND_MSG = _('Not found in database')
NOT_FOUND_MSG_COLORED = '<font color=red>%s</font>' % NOT_FOUND_MSG
READ_ERROR_MSG = _('File reading error')
READ_ERROR_MSG_COLORED = '<font color=red>%s</font>' % READ_ERROR_MSG


class DataImportWizard(QDialog):
    sig_data_about_to_be_updated = Signal()
    sig_data_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_('Data Import Wizard'))
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setModal(False)
        self.resize(650, 600)

        self._table_id = 'data_import_wizard'
        self._libraries = {
            'sonde_data': None,
            'sonde_models_lib': None,
            'sonde_installations': None,
            'observation_wells_data': None}

        self._sonde_serial_no = None
        self._obs_well_uuid = None
        self._sonde_depth = None

        # Setup file info.
        self.filename_label = QLabel()
        self.serial_number_label = QLabel()
        self.projectid_label = QLabel()
        self.site_name_label = QLabel()

        file_groupbox = QGroupBox(_('File Info'))
        file_layout = QFormLayout(file_groupbox)
        file_layout.addRow(_('File') + ' :', self.filename_label)
        file_layout.addRow(_('Project ID') + ' :', self.projectid_label)
        file_layout.addRow(_('Location') + ' :', self.site_name_label)
        file_layout.addRow(_('Serial Number') + ' :', self.serial_number_label)

        # Setup sonde info.
        self.sonde_label = QLabel()
        self.obs_well_label = QLabel()
        self.install_depth = QLabel()
        self.install_period = QLabel()

        sonde_groupbox = QGroupBox(_('Sonde Installation Info'))
        sonde_layout = QFormLayout(sonde_groupbox)
        sonde_layout.addRow(_('Sonde') + ' :', self.sonde_label)
        sonde_layout.addRow(_('Well') + ' :', self.obs_well_label)
        sonde_layout.addRow(_('Depth') + ' :', self.install_depth)
        sonde_layout.addRow(_('Period') + ' :', self.install_period)

        # Setup the table widget.
        class ImportDataTableModel(SardesTableModel):
            def create_delegate_for_column(self, view, column):
                return NotEditableDelegate(self)

        self.table_model = ImportDataTableModel(
            table_title='Logger Data',
            table_id='logger_data',
            data_columns_mapper=[])
        self.table_widget = SardesTableWidget(
            self.table_model, multi_columns_sort=False,
            sections_movable=False, sections_hidable=False,
            disabled_actions=SardesTableWidget.EDIT_ACTIONS)
        horizontal_header = self.table_widget.tableview.horizontalHeader()
        horizontal_header.setDefaultSectionSize(100)

        # Setup the dialog button box.
        self.next_btn = QPushButton(_('Next'))
        self.next_btn.setDefault(True)
        self.close_btn = QPushButton(_('Close'))
        self.close_btn.setDefault(False)
        self.close_btn.setAutoDefault(False)
        self.load_btn = QPushButton(_('Load Data'))
        self.load_btn.setDefault(False)
        self.load_btn.setAutoDefault(False)

        button_box = QDialogButtonBox()
        button_box.addButton(self.load_btn, button_box.ActionRole)
        button_box.addButton(self.next_btn, button_box.ApplyRole)
        button_box.addButton(self.close_btn, button_box.RejectRole)
        button_box.layout().insertSpacing(1, 100)
        button_box.clicked.connect(self._handle_button_click_event)

        # Setup the layout.
        layout = QVBoxLayout(self)
        layout.addWidget(file_groupbox)
        layout.addWidget(sonde_groupbox)
        layout.addWidget(self.table_widget)
        layout.addWidget(button_box)

        self._working_dir = get_home_dir()
        self._queued_filenames = []

    @property
    def working_directory(self):
        """
        Return the directory that by the QFileDialog to get open file names.
        """
        return (self._working_dir if
                osp.exists(self._working_dir) else
                get_home_dir())

    @working_directory.setter
    def working_directory(self, new_working_dir):
        """
        Set the directory that by the QFileDialog to get open file names.
        """
        if new_working_dir is not None and osp.exists(new_working_dir):
            self._working_dir = new_working_dir

    def show(self):
        self._queued_filenames, _ = QFileDialog.getOpenFileNames(
            self.parent(), 'Select data files',
            self.working_directory, '*.csv ; *.lev ; *.xle')

        if len(self._queued_filenames):
            self._load_next_queued_data_file()
            super().show()

    # ---- Sardes Model Public API
    def set_database_connection_manager(self, db_connection_manager):
        """Setup the namespace for the database connection manager."""
        self.db_connection_manager = db_connection_manager

    def set_model_data(self, dataf):
        """
        Set the data needed by the wizard and update the info displayed
        in the GUI.
        """
        self.set_model_library(dataf, 'sonde_data')

    def set_model_library(self, dataf, name):
        """
        Set the data for the given library name and update the info
        displayed in the GUI.
        """
        self._libraries[name] = dataf
        self._update_sonde_info()
        self._update_button_state()

    def clear_data(self):
        """Clear the data of this wizard table."""
        self.table_model.clear_data()

    # ---- Private API
    def _load_next_queued_data_file(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        filename = self._queued_filenames.pop(0)
        self.working_directory = osp.dirname(filename)
        self.filename_label.setText(filename)
        self.filename_label.setToolTip(filename)
        try:
            self._file_reader = hsr.SolinstFileReader(filename)
        except:
            self._file_reader = None
            self._sonde_serial_no = None
            self.serial_number_label.setText(READ_ERROR_MSG_COLORED)
            self.site_name_label.setText(READ_ERROR_MSG_COLORED)
            self.projectid_label.setText(READ_ERROR_MSG_COLORED)
        else:
            sites = self._file_reader.sites
            self.serial_number_label.setText(sites.instrument_serial_number)
            self.site_name_label.setText(sites.site_name)
            self.projectid_label.setText(sites.project_name)
            self._sonde_serial_no = sites.instrument_serial_number or None
        self._update_sonde_info()
        self._update_table_model_data()
        self._update_button_state()
        QApplication.restoreOverrideCursor()

    def _update_table_model_data(self):
        """
        Format and update the data shown in the timeseries table.
        """
        if self._file_reader.records is not None:
            dataf = self._file_reader.records
            dataf.insert(0, 'Datetime', dataf.index)
            dataf.rename(columns={'Datetime': 'datetime'}, inplace=True)
            for column in dataf.columns:
                if column.lower().startswith('level'):
                    # We convert into meters.
                    if column.lower().endswith('cm'):
                        dataf[column] = dataf[column] / 100
                    # We convert water height in depth below top of casing.
                    if self._sonde_depth is not None:
                        dataf[column] = self._sonde_depth - dataf[column]
                    dataf.rename(columns={column: DataType.WaterLevel},
                                 inplace=True)
                elif column.lower().startswith('temp'):
                    dataf.rename(columns={column: DataType.WaterTemp},
                                 inplace=True)
            dataf_columns_mapper = [('datetime', _('Datetime'))]
            dataf_columns_mapper.extend([(dtype, dtype.label) for dtype in
                                         DataType if dtype in dataf.columns])
            self.table_model.set_model_data(dataf, dataf_columns_mapper)

    def _update_sonde_info(self):
        """
        Update sonde information.
        """
        # Update sonde brand model serial info.
        sonde_uuid = self._get_sonde_uuid()
        sonde_model_id = self._get_sonde_model_id()
        if sonde_uuid is not None:
            try:
                sonde_brand_model = self._libraries['sonde_models_lib'].loc[
                    sonde_model_id, 'sonde_brand_model']
            except (KeyError, IndexError):
                self.sonde_label.setText(NOT_FOUND_MSG_COLORED)
            else:
                self.sonde_label.setText('{} {}'.format(
                    sonde_brand_model, self._sonde_serial_no))
        else:
            self.sonde_label.setText(NOT_FOUND_MSG_COLORED)

        # Update well id and municipality.
        install_data = self._get_installation_data()
        if install_data is not None:
            self._obs_well_uuid = install_data['sampling_feature_uuid']
            self._sonde_depth = install_data['install_depth']
            try:
                well_name = self._libraries['observation_wells_data'].loc[
                    self._obs_well_uuid, 'obs_well_id']
                municipality = self._libraries['observation_wells_data'].loc[
                    self._obs_well_uuid, 'municipality']
            except (KeyError, IndexError):
                self.obs_well_label.setText(NOT_FOUND_MSG_COLORED)
                self.install_depth.setText(NOT_FOUND_MSG_COLORED)
                self.install_period.setText(NOT_FOUND_MSG_COLORED)
            else:
                self.obs_well_label.setText('{} ({})'.format(
                    well_name, municipality))
                self.install_depth.setText('{} m'.format(
                    str(install_data['install_depth'])))
                self.install_period.setText('{} to {}'.format(
                    install_data['start_date'].strftime("%m-%d-%Y %H:%M"),
                    '...' if pd.isnull(install_data['end_date']) else
                    install_data['end_date'].strftime("%Y-%m-%d %H:%M")))
        else:
            self._obs_well_uuid = None
            self._sonde_depth = None
            self.obs_well_label.setText(NOT_FOUND_MSG_COLORED)
            self.install_depth.setText(NOT_FOUND_MSG_COLORED)
            self.install_period.setText(NOT_FOUND_MSG_COLORED)

    def _get_sonde_uuid(self):
        """
        Return the sonde uuid corresponding to sonde serial number of the
        currently opened data file.
        """
        if self._sonde_serial_no is None:
            return None
        try:
            sonde_uuid = (
                self._libraries['sonde_data']
                [self._libraries['sonde_data']['sonde_serial_no'] ==
                 self._sonde_serial_no]
                .index[0])
            return sonde_uuid
        except (KeyError, IndexError):
            return None

    def _get_sonde_model_id(self):
        """
        Return the model id of the sonde associated with the currently
        opened data file.
        """
        if self._sonde_serial_no is None:
            return None
        try:
            sonde_model_id = (
                self._libraries['sonde_data']
                [self._libraries['sonde_data']['sonde_serial_no'] ==
                 self._sonde_serial_no]
                ['sonde_model_id']
                .values[0])
            return sonde_model_id
        except (KeyError, IndexError):
            return None

    def _get_installation_data(self):
        """
        Return the installation data associated with the sonde uuid and date
        range of the data.
        """
        sonde_uuid = self._get_sonde_uuid()
        if sonde_uuid is None:
            return None
        try:
            installs = (
                self._libraries['sonde_installations']
                [self._libraries['sonde_installations']['sonde_uuid'] ==
                 sonde_uuid]
                )
        except (KeyError, IndexError):
            return None
        else:
            avg_datetime = self._file_reader.records.index.mean()
            for i in range(len(installs)):
                install = installs.iloc[i]
                start_date = install['start_date']
                end_date = (install['end_date'] if
                            not pd.isnull(install['end_date']) else
                            datetime.datetime.now())
                if start_date <= avg_datetime and end_date >= avg_datetime:
                    return install
            else:
                return None

    def _update_button_state(self):
        """Update the state of the dialog's buttons."""
        self.next_btn.setEnabled(len(self._queued_filenames) > 0)
        self.load_btn.setEnabled(self._obs_well_uuid is not None)

    @Slot(QAbstractButton)
    def _handle_button_click_event(self, button):
        """
        Handle when a button is clicked on the dialog button box.
        """
        if button == self.close_btn:
            self.close()
        elif button == self.next_btn:
            self._load_next_queued_data_file()