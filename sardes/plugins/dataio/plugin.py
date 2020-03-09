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
                            QFormLayout)

# ---- Local imports
from sardes.config.main import CONF
from sardes.api.plugins import SardesPlugin
from sardes.api.tablemodels import SardesTableModel
from sardes.config.icons import get_icon
from sardes.config.locale import _
from sardes.utils.qthelpers import (
    create_mainwindow_toolbar, create_toolbutton)
from sardes.widgets.tableviews import NotEditableDelegate, SardesTableWidget


"""Data Input/Output plugin"""


NOT_FOUND_MSG = _('Not found in database')
NOT_FOUND_MSG_COLORED = '<font color=red>%s</font>' % NOT_FOUND_MSG


class DataIO(SardesPlugin):

    CONF_SECTION = 'data_io'

    def __init__(self, parent):
        super().__init__(parent)

    # ---- SardesPlugin Public API
    @classmethod
    def get_plugin_title(cls):
        """Return widget title"""
        return _('Data Import Wizard')

    def setup_plugin(self):
        """Setup this plugin."""
        self.data_import_wizard = DataImportWizard(self.main)

    def create_mainwindow_toolbars(self):
        toolbar = create_mainwindow_toolbar("Data Import Wizard toolbar")

        # Setup the database connection button.
        data_import_button = create_toolbutton(
            self.main, triggered=self._show_data_import_wizard,
            text=_("Import Data..."),
            tip=_("Open a wizard to import new monitoring data."),
            icon='file_import'
            )
        toolbar.addWidget(data_import_button)

        return [toolbar]

    def close_plugin(self):
        """
        Extend Sardes plugin method to save user inputs in the
        configuration file.
        """
        super().close_plugin()

        # Save the import wizard working dir.
        self.set_option(
            'wiz_workdir', self.data_import_wizard.working_directory)

    def register_plugin(self):
        """
        Extend base class method to do some connection with the database
        manager to update the tables' data.
        """
        super().register_plugin()
        self.main.db_connection_manager.register_model(
            self.data_import_wizard,
            'sondes_data',
            ['sonde_models_lib', 'sonde_installations',
             'observation_wells_data'])

        # Set the import wizard working dir.
        self.data_import_wizard.working_directory = self.get_option(
            'wiz_workdir', None)

    # ---- Private API
    def _show_data_import_wizard(self):
        self._update_data_import_wizard()
        self.data_import_wizard.show()

    def _update_data_import_wizard(self):
        self.main.db_connection_manager.update_model('data_import_wizard')


class ImportDataTableModel(SardesTableModel):
    """
    A table model to display imported raw logger data.
    """

    def create_delegate_for_column(self, view, column):
        """
        Create the item delegate that the view need to use when editing the
        data of this model for the specified column. If None is returned,
        the items of the column will not be editable.
        """
        return NotEditableDelegate(self)


class DataImportWizard(QDialog):
    sig_data_about_to_be_updated = Signal()
    sig_data_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_('Data Import Wizard'))
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setModal(False)

        self._table_id = 'data_import_wizard'
        self._sonde_data = None
        self._sonde_models_lib = None
        self._sonde_installations = None
        self._observation_wells_data = None

        self._sonde_serial_no = None
        self._avg_datetime = None
        self._sonde_model_id = None
        self._sonde_uuid = None
        self._obs_well_uuid = None

        # Setup file info.
        self.filename_label = QLabel()
        self.serial_number_label = QLabel()
        self.model_label = QLabel()
        self.obs_well_label = QLabel()
        self.location_label = QLabel()
        self.visit_date = QLabel()

        self.form_layout = QFormLayout()
        self.form_layout.addRow(_('File') + ' :', self.filename_label)
        self.form_layout.addRow(
            _('Serial Number') + ' :', self.serial_number_label)
        self.form_layout.addRow(_('Model') + ' :', self.model_label)
        self.form_layout.addRow(_('Well') + ' :', self.obs_well_label)
        self.form_layout.addRow(_('Location') + ' :', self.location_label)
        self.form_layout.addRow(_('Visit Date') + ' :', self.visit_date)

        # Setup the table widget.
        self.table_model = ImportDataTableModel(
            table_title='Logger Data',
            table_id='logger_data',
            data_columns_mapper=[])
        self.table_widget = SardesTableWidget(
            self.table_model, multi_columns_sort=False,
            sections_movable=False, sections_hidable=False,
            disabled_actions=['edit'])

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
        layout.addLayout(self.form_layout)
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

    def _load_next_queued_data_file(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        filename = self._queued_filenames.pop(0)
        self.working_directory = osp.dirname(filename)
        self.filename_label.setText(osp.basename(filename))
        self.filename_label.setToolTip(filename)
        try:
            solinst_file = hsr.SolinstFileReader(filename)
        except:
            pass
        else:
            sites = solinst_file.sites
            self._sonde_serial_no = sites.instrument_serial_number or None
            self.location_label.setText(sites.site_name)
            self.visit_date.setText(
                sites.visit_date.strftime("%Y-%m-%d %H:%M:%S"))

            dataf = solinst_file.records
            dataf.insert(0, 'Datetime', dataf.index)
            self._avg_datetime = dataf.index.mean()

            self.table_model.set_model_data(
                dataf, [(col, col) for col in dataf.columns])
            self.table_widget.tableview._setup_item_delegates()
            self.table_widget.tableview.resizeColumnsToContents()
        self._update_sonde_info()
        self._update_button_state()
        QApplication.restoreOverrideCursor()

    # ---- Sardes Model Public API
    def set_database_connection_manager(self, db_connection_manager):
        """Setup the namespace for the database connection manager."""
        self.db_connection_manager = db_connection_manager

    def set_model_data(self, dataf):
        """
        Set the data needed by the wizard and update the info displayed
        in the GUI.
        """
        self._sonde_data = dataf
        self._update_sonde_info()
        self._update_button_state()

    def set_model_library(self, dataf, name):
        """
        Set the data for the given library name and update the info
        displayed in the GUI.
        """
        setattr(self, '_' + name, dataf)
        self._update_sonde_info()
        self._update_button_state()

    def clear_data(self):
        """Clear the data of this wizard table."""
        self.table_model.clear_data()

    # ---- Private API
    def _update_sonde_info(self):
        self._sonde_uuid = self._fetch_sonde_uuid()
        self._sonde_model_id = self._fetch_sonde_model_id()
        self._obs_well_uuid = self._fetch_obs_well_uuid()

        self._update_sonde_serial_number()
        self._update_sonde_model()
        self._update_well()
        self._update_well_municipality()

    def _fetch_sonde_uuid(self):
        """
        Fetch and return the sonde uuid corresponding to sonde serial number
        of the currently opened data file.
        """
        if self._sonde_serial_no is None:
            return None
        try:
            sonde_uuid = (
                self._sonde_data
                [self._sonde_data['sonde_serial_no'] == self._sonde_serial_no]
                .index[0])
            return sonde_uuid
        except (KeyError, IndexError):
            return None

    def _fetch_sonde_model_id(self):
        """
        Fetch and return the model id of the sonde associated
        with the currently opened data file.
        """
        if self._sonde_serial_no is None:
            return None
        try:
            sonde_model_id = (
                self._sonde_data
                [self._sonde_data['sonde_serial_no'] == self._sonde_serial_no]
                ['sonde_model_id']
                .values[0])
            return sonde_model_id
        except (KeyError, IndexError):
            return None

    def _fetch_obs_well_uuid(self):
        """
        Fetch and return the observation well uuid where the sonde associated
        with the currently opened data file was installed.
        """
        if self._sonde_uuid is None:
            return None
        try:
            installs = (
                self._sonde_installations
                [self._sonde_installations['sonde_uuid'] == self._sonde_uuid]
                )
            for i in range(len(installs)):
                install = installs.iloc[i]
                start_date = install['start_date']
                end_date = (install['end_date'] if
                            not pd.isnull(install['end_date']) else
                            datetime.datetime.now())
                if (start_date <= self._avg_datetime and
                        end_date >= self._avg_datetime):
                    return install['sampling_feature_uuid']
            else:
                return None
        except (KeyError, IndexError):
            return None

    def _update_sonde_serial_number(self):
        """Update the sonde serial number."""
        self.serial_number_label.setText(
            self._sonde_serial_no if self._sonde_serial_no is not None else
            NOT_FOUND_MSG_COLORED)

    def _update_well_municipality(self):
        """Update the location of the well in which the sonde is installed."""
        if self._obs_well_uuid is not None:
            try:
                location = self._observation_wells_data.loc[
                    self._obs_well_uuid, 'municipality']
                self.location_label.setText(location)
            except (KeyError, IndexError):
                self.location_label.setText(NOT_FOUND_MSG_COLORED)
        else:
            self.location_label.setText(NOT_FOUND_MSG_COLORED)

    def _update_sonde_model(self):
        """Update the sonde model."""
        if self._sonde_model_id is not None:
            try:
                sonde_brand_model = self._sonde_models_lib.loc[
                    self._sonde_model_id, 'sonde_brand_model']
                self.model_label.setText(sonde_brand_model)
            except (KeyError, IndexError):
                self.model_label.setText(NOT_FOUND_MSG_COLORED)
                self._sonde_model_id = None
        else:
            self.model_label.setText(NOT_FOUND_MSG_COLORED)

    def _update_well(self):
        """
        Update the well id in which the sensor is installed.
        """
        if self._obs_well_uuid is not None:
            try:
                well_id = self._observation_wells_data.loc[
                    self._obs_well_uuid, 'obs_well_id']
                self.obs_well_label.setText(well_id)
            except (KeyError, IndexError):
                self.obs_well_label.setText(NOT_FOUND_MSG_COLORED)
        else:
            self.obs_well_label.setText(NOT_FOUND_MSG_COLORED)

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
