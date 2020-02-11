# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports
import os.path as osp

# ---- Third party imports
from appconfigs.base import get_home_dir
import hydsensread as hsr
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
            self.data_import_wizard, 'sondes_data', ['sonde_models_lib'])

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

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(_('Data Import Wizard'))
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setModal(False)

        self._table_id = 'data_import_wizard'
        self._sonde_brand_model = None
        self._sonde_models_lib = None

        # Setup file info.
        self.filename_label = QLabel()
        self.serial_number_label = QLabel()
        self.model_label = QLabel()
        self.obs_well_label = QLabel()
        self.project_id_label = QLabel()
        self.location_label = QLabel()
        self.visit_date = QLabel()

        form_layout = QFormLayout()
        form_layout.addRow(_('File') + ' :', self.filename_label)
        form_layout.addRow(_('Serial Number') + ' :', self.serial_number_label)
        form_layout.addRow(_('Model') + ' :', self.model_label)
        form_layout.addRow(_('Well') + ' :', self.obs_well_label)
        form_layout.addRow(_('Project ID') + ' :', self.project_id_label)
        form_layout.addRow(_('Location') + ' :', self.location_label)
        form_layout.addRow(_('Visit Date') + ' :', self.visit_date)

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
        self.close_button = QPushButton(_('Close'))
        self.close_button.setDefault(False)
        self.close_button.setAutoDefault(False)

        button_box = QDialogButtonBox()
        button_box.addButton(self.next_btn, button_box.ApplyRole)
        button_box.addButton(self.close_button, button_box.RejectRole)
        button_box.layout().insertSpacing(1, 100)
        button_box.clicked.connect(self._handle_button_click_event)

        # Setup the layout.
        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
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
            self._load_next_queud_data_file()
            super().show()

    def _load_next_queud_data_file(self):
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
            self.serial_number_label.setText(sites.instrument_serial_number)
            self.project_id_label.setText(sites.project_name)
            self.location_label.setText(sites.site_name)
            self.visit_date.setText(
                sites.visit_date.strftime("%Y-%m-%d %H:%M:%S"))

            dataf = solinst_file.records
            dataf.insert(0, 'Datetime', dataf.index)

            self.table_model.set_model_data(
                dataf, [(col, col) for col in dataf.columns])
            self.table_widget.tableview._setup_item_delegates()
            self.table_widget.tableview.resizeColumnsToContents()
        self._update_sonde_model()
        self._update_button_state()

    # ---- Sardes Model Public API
    def set_database_connection_manager(self, db_connection_manager):
        """Setup the namespace for the database connection manager."""
        self.db_connection_manager = db_connection_manager

    def set_model_data(self, dataf):
        self._sonde_brand_model = dataf
        self._update_sonde_model()

    def set_model_library(self, dataf, name):
        self._sonde_models_lib = dataf
        self._update_sonde_model()

    # ---- Private API
    def _update_sonde_model(self):
        """Update the sonde model shown in dialog."""
        serial_number = self.serial_number_label.text()
        if self._sonde_models_lib is not None and serial_number != '':
            model = (self._sonde_brand_model[
                self._sonde_brand_model['sonde_serial_no'] == serial_number
                ]['sonde_model_id'].values[0])
            sonde_brand_model = self._sonde_models_lib.loc[
                model, 'sonde_brand_model']
            self.model_label.setText(sonde_brand_model)
        else:
            self.model_label.setText('')

    def _update_button_state(self):
        """Update the state of the dialog's buttons."""
        self.next_btn.setEnabled(len(self._queued_filenames) > 0)

    @Slot(QAbstractButton)
    def _handle_button_click_event(self, button):
        """
        Handle when a button is clicked on the dialog button box.
        """
        if button == self.close_button:
            self.close()
        elif button == self.next_btn:
            self._load_next_queud_data_file()
