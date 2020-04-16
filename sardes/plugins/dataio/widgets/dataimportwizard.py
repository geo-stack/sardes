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
import datetime
import os.path as osp

# ---- Third party imports
from appconfigs.base import get_home_dir
from atomicwrites import replace_atomic
from hydsensread import SolinstFileReader
import pandas as pd
from qtpy.QtCore import Qt, Slot, Signal
from qtpy.QtWidgets import (
    QApplication, QFileDialog, QDialog, QLabel, QPushButton, QDialogButtonBox,
    QAbstractButton, QFormLayout, QGroupBox, QMessageBox, QGridLayout,
    QFrame, QStackedWidget)

# ---- Local imports
from sardes.config.gui import get_iconsize, RED
from sardes.config.locale import _
from sardes.api.tablemodels import SardesTableModel
from sardes.api.timeseries import DataType, merge_timeseries_groups
from sardes.utils.qthelpers import create_toolbutton
from sardes.widgets.tableviews import NotEditableDelegate, SardesTableWidget
from sardes.widgets.buttons import CheckboxPathBoxWidget


NOT_FOUND_MSG = _('Not found in database')
NOT_FOUND_MSG_COLORED = '<font color=red>%s</font>' % NOT_FOUND_MSG
READ_ERROR_MSG = _('File reading error')
READ_ERROR_MSG_COLORED = '<font color=red>%s</font>' % READ_ERROR_MSG


class ImportDataTableModel(SardesTableModel):
    def create_delegate_for_column(self, view, column):
        return NotEditableDelegate(self)


class DataImportWizard(QDialog):
    sig_view_data = Signal(object)
    sig_installation_info_uptated = Signal()
    sig_previous_data_uptated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_('Data Import Wizard'))
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setModal(False)
        self.resize(650, 600)

        self._data_is_loading = False
        self._data_is_loaded = False
        self._file_reader = None

        self._libraries = {
            'sondes_data': None,
            'sonde_models_lib': None,
            'sonde_installations': None,
            'observation_wells_data': None}

        self._filename = None
        self._sonde_serial_no = None
        self._obs_well_uuid = None
        self._sonde_depth = None
        self._install_id = None

        # Setup file info.
        self.filename_label = QLabel()
        self.serial_number_label = QLabel()
        self.projectid_label = QLabel()
        self.site_name_label = QLabel()

        file_groupbox = QGroupBox(_('File Info'))
        file_layout = QFormLayout(file_groupbox)
        file_layout.addRow(_('Input File') + ' :', self.filename_label)
        file_layout.addRow(_('Project ID') + ' :', self.projectid_label)
        file_layout.addRow(_('Location') + ' :', self.site_name_label)
        file_layout.addRow(_('Serial Number') + ' :', self.serial_number_label)

        # Setup sonde installation info.
        self.sonde_label = QLabel()
        self.obs_well_label = QLabel()
        self.install_depth = QLabel()
        self.install_period = QLabel()

        sonde_info_widget = QFrame()
        sonde_form = QFormLayout(sonde_info_widget)
        sonde_form.addRow(_('Sonde') + ' :', self.sonde_label)
        sonde_form.addRow(_('Well') + ' :', self.obs_well_label)
        sonde_form.addRow(_('Depth') + ' :', self.install_depth)
        sonde_form.addRow(_('Period') + ' :', self.install_period)

        self.sonde_msg_label = QLabel()
        self.sonde_msg_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.sonde_msg_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.sonde_msg_label.setWordWrap(True)

        self.sonde_stacked_widget = QStackedWidget()
        self.sonde_stacked_widget.addWidget(sonde_info_widget)
        self.sonde_stacked_widget.addWidget(self.sonde_msg_label)
        
        sonde_groupbox = QGroupBox(_('Sonde Installation Info'))
        sonde_groupbox_layout = QGridLayout(sonde_groupbox)
        sonde_groupbox_layout.addWidget(self.sonde_stacked_widget)

        # Setup comparison with previous data.
        self.previous_date_label = QLabel()
        self.previous_level_label = QLabel()
        self.delta_level_label = QLabel()
        self.delta_date_label = QLabel()

        previous_widget = QFrame()
        previous_layout = QGridLayout(previous_widget)
        previous_layout.addWidget(QLabel(_('Previous Date') + ' :'), 0, 0)
        previous_layout.addWidget(self.previous_date_label, 0, 1)
        previous_layout.addWidget(QLabel(_('Delta Date') + ' :'), 1, 0)
        previous_layout.addWidget(self.delta_date_label, 1, 1)
        previous_layout.addWidget(
            QLabel(_('Previous Water Level') + ' :'), 2, 0)
        previous_layout.addWidget(self.previous_level_label, 2, 1)
        previous_layout.addWidget(
            QLabel(_('Delta Water Level') + ' :'), 3, 0)
        previous_layout.addWidget(self.delta_level_label, 3, 1)

        previous_layout.setRowStretch(4, 1)
        previous_layout.setColumnStretch(2, 1)
        previous_layout.setContentsMargins(0, 0, 0, 0)

        self.previous_msg_label = QLabel()
        self.previous_msg_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.previous_msg_label.setTextInteractionFlags(
            Qt.TextBrowserInteraction)
        self.previous_msg_label.setWordWrap(True)
        self.previous_msg_label.hide()

        self.previous_stacked_widget = QStackedWidget()
        self.previous_stacked_widget.addWidget(previous_widget)
        self.previous_stacked_widget.addWidget(self.previous_msg_label)

        previous_groupbox = QGroupBox(_('Previous Reading'))
        previous_groupbox_layout = QGridLayout(previous_groupbox)
        previous_groupbox_layout.addWidget(self.previous_stacked_widget)
        
        # Make all label selectable with the mouse cursor.
        for layout in [file_layout, sonde_form, previous_layout]:
            for index in range(layout.count()):
                try:
                    layout.itemAt(index).widget().setTextInteractionFlags(
                        Qt.TextBrowserInteraction)
                except AttributeError:
                    pass

        # Setup the table widget.
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

        # Add extra toolbar buttons.
        self.show_data_btn = create_toolbutton(
            self,
            icon='show_data_table',
            text=_("View data"),
            tip=_('Show the data of the timeseries acquired in the currently '
                  'selected observation well in a table.'),
            triggered=lambda _: self._view_timeseries_data(),
            iconsize=get_iconsize()
            )
        self.table_widget.add_toolbar_separator()
        self.table_widget.add_toolbar_widget(self.show_data_btn)

        # Setup the dialog button box.
        self.next_btn = QPushButton(_('Next'))
        self.next_btn.setDefault(True)
        self.close_btn = QPushButton(_('Close'))
        self.close_btn.setDefault(False)
        self.close_btn.setAutoDefault(False)
        self.load_btn = QPushButton(_('Load Data'))
        self.load_btn.setDefault(False)
        self.load_btn.setAutoDefault(False)

        self.button_box = QDialogButtonBox()
        self.button_box.addButton(self.load_btn, self.button_box.ActionRole)
        self.button_box.addButton(self.next_btn, self.button_box.ApplyRole)
        self.button_box.addButton(self.close_btn, self.button_box.RejectRole)
        self.button_box.layout().insertSpacing(1, 100)
        self.button_box.clicked.connect(self._handle_button_click_event)

        self.pathbox_widget = CheckboxPathBoxWidget(
            label=_('Move the input file to this location after loading data'))

        # Setup the layout.
        layout = QGridLayout(self)
        layout.addWidget(file_groupbox, 0, 0, 1, 2)
        layout.addWidget(sonde_groupbox, 1, 0)
        layout.addWidget(previous_groupbox, 1, 1)
        layout.addWidget(self.table_widget, 2, 0, 1, 2)
        layout.setRowStretch(2, 1)
        layout.setRowMinimumHeight(3, 25)
        layout.addWidget(self.pathbox_widget, 4, 0, 1, 2)
        layout.setRowMinimumHeight(5, 5)
        layout.addWidget(self.button_box, 6, 0, 1, 2)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)

        self._working_dir = get_home_dir()
        self._queued_filenames = []

        self.sig_installation_info_uptated.connect(self._update_previous_data)
        self.sig_installation_info_uptated.connect(
            self._update_table_model_data)
        self.sig_previous_data_uptated.connect(self._update_button_state)

    @property
    def filename(self):
        """
        Return the name of the input data file currently opened in the wizard.
        """
        return self._filename

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

    @property
    def tseries_dataf(self):
        """
        Return the pandas dataframe containing the timeseries data'for the
        currently opened file in the wizard.
        """
        return self.table_model.dataf

    # ---- Connection with Database
    def set_database_connection_manager(self, db_connection_manager):
        """Setup the namespace for the database connection manager."""
        self.db_connection_manager = db_connection_manager
        self.db_connection_manager.sig_database_connection_changed.connect(
            self._handle_database_connection_changed)

    def _handle_database_connection_changed(self, connected):
        """
        Handle when the connection to the database change.
        """
        self._update_installation_info()

    # ---- Private API
    def _update_installation_info(self):
        """
        Update sonde installation info.
        """
        if self._sonde_serial_no is not None:
            self.db_connection_manager.get_sonde_installation_info(
                self._sonde_serial_no,
                self._file_reader.records.index.mean(),
                callback=self._set_installation_info)
        else:
            self._set_installation_info(None)

    def _set_installation_info(self, sonde_install_data):
        """
        Set sonde installation info.
        """
        self._obs_well_uuid = None
        self._sonde_depth = None
        self._install_id = None
        if self._file_reader is None:
            self.sonde_label.clear()
            self.obs_well_label.clear()
            self.install_depth.clear()
            self.install_period.clear()
            self.sonde_stacked_widget.setCurrentIndex(0)
        elif not self.db_connection_manager.is_connected():
            self.sonde_msg_label.setText(
                _('Info not available because not connected to a database.'))
            self.sonde_stacked_widget.setCurrentIndex(1)
        elif sonde_install_data is not None:
            self._install_id = sonde_install_data.name
            self._obs_well_uuid = sonde_install_data['sampling_feature_uuid']
            self._sonde_depth = sonde_install_data['install_depth']

            self.sonde_label.setText('{} {}'.format(
                sonde_install_data['sonde_brand_model'],
                self._sonde_serial_no
                ))
            self.obs_well_label.setText('{} ({})'.format(
                sonde_install_data['well_name'],
                sonde_install_data['well_municipality']
                ))
            self.install_depth.setText('{} m'.format(
                str(sonde_install_data['install_depth'])
                ))
            self.install_period.setText('{} to {}'.format(
                sonde_install_data['start_date'].strftime("%Y-%m-%d %H:%M"),
                _('today') if pd.isnull(sonde_install_data['end_date']) else
                sonde_install_data['end_date'].strftime("%Y-%m-%d %H:%M")
                ))
            self.sonde_stacked_widget.setCurrentIndex(0)
        else:
            self.sonde_label.setText(NOT_FOUND_MSG_COLORED)
            self.obs_well_label.setText(NOT_FOUND_MSG_COLORED)
            self.install_depth.setText(NOT_FOUND_MSG_COLORED)
            self.install_period.setText(NOT_FOUND_MSG_COLORED)
            self.sonde_stacked_widget.setCurrentIndex(0)
        self.sig_installation_info_uptated.emit()

    def _update_previous_data(self):
        """
        Update the information regarding the water level reading that is
        stored in the database previous to the data series contained in
        the data file.
        """
        if (self._obs_well_uuid is not None and
                self.db_connection_manager.is_connected()):
            self.db_connection_manager.get_timeseries_for_obs_well(
                self._obs_well_uuid, [DataType.WaterLevel],
                self._set_previous_data)
        else:
            self._set_previous_data(None)

    def _clear_previous_data(self):
        """
        Clear the data shown in the previous data group box.
        """
        self.previous_stacked_widget.setCurrentIndex(0)
        self.previous_date_label.clear()
        self.previous_level_label.clear()
        self.delta_level_label.clear()
        self.delta_date_label.clear()
        self.sig_previous_data_uptated.emit()

    def _set_previous_data(self, tseries_groups):
        """
        Set the information regarding the water level reading that is
        stored in the database previous to the data series contained in
        the data file.
        """
        if not self.db_connection_manager.is_connected():
            self.previous_msg_label.setText(
                _('Info not available because not connected to a database.'))
            self.previous_stacked_widget.setCurrentIndex(1)
            self.sig_previous_data_uptated.emit()
            return

        if tseries_groups is None:
            self._clear_previous_data()
            return

        prev_dataf = merge_timeseries_groups(tseries_groups)
        new_dataf = self.table_model.dataf
        if (DataType.WaterLevel not in prev_dataf.columns or
                DataType.WaterLevel not in new_dataf.columns):
            self._clear_previous_data()
            return

        new_series = pd.Series(
            new_dataf[DataType.WaterLevel].values,
            index=new_dataf['datetime']).dropna()
        if not len(new_series):
            self._clear_previous_data()
            return

        prev_series = pd.Series(
            prev_dataf[DataType.WaterLevel].values,
            index=prev_dataf['datetime']).dropna()
        prev_series = prev_series[
            prev_series.index < new_series.index[0]]
        if not len(prev_series):
            self.previous_msg_label.setText(
                _('There is no water level stored in the database '
                  'for well {} before {}.').format(
                      self.obs_well_label.text(),
                      new_series.index[0].strftime("%Y-%m-%d %H:%M")))
            self.previous_stacked_widget.setCurrentIndex(1)
            self.sig_previous_data_uptated.emit()
            return

        self.previous_stacked_widget.setCurrentIndex(0)
        prev_level = prev_series.iat[-1]
        delta_level = new_series.iat[0] - prev_level
        prev_datetime = prev_series.index[-1]
        delta_datetime = (new_series.index[0] - prev_datetime)
        self.previous_level_label.setText('{:0.6f}'.format(prev_level))
        self.delta_level_label.setText('{:0.6f}'.format(delta_level))
        self.previous_date_label.setText(
            prev_datetime.strftime("%Y-%m-%d %H:%M"))
        self.delta_date_label.setText(
            '{:0.0f} {} {:0.0f} {} {:0.0f} {}'.format(
                delta_datetime.days, _('days'),
                delta_datetime.seconds // 3600, _('hrs'),
                (delta_datetime.seconds // 60) % 60, _('mins')
                ))
        self.sig_previous_data_uptated.emit()

    def _load_next_queued_data_file(self):
        """
        Load the data from the next file in the queue.
        """
        self.table_widget._start_process(_('Loading data...'))
        self._data_is_loaded = False
        self._filename = self._queued_filenames.pop(0)
        self.working_directory = osp.dirname(self._filename)
        self.filename_label.setText(osp.basename(self._filename))
        self.filename_label.setToolTip(self._filename)
        try:
            self._file_reader = SolinstFileReader(self._filename)
        except Exception as e:
            _error = e
            self._file_reader = None
            self._sonde_serial_no = None
            self.serial_number_label.setText(READ_ERROR_MSG_COLORED)
            self.site_name_label.setText(READ_ERROR_MSG_COLORED)
            self.projectid_label.setText(READ_ERROR_MSG_COLORED)
            status_msg = _('Failed to load data.')
        else:
            _error = None
            sites = self._file_reader.sites
            self.serial_number_label.setText(sites.instrument_serial_number)
            self.site_name_label.setText(sites.site_name)
            self.projectid_label.setText(sites.project_name)
            self._sonde_serial_no = sites.instrument_serial_number or None
            status_msg = _('Data loaded sucessfully.')
        self._update_installation_info()
        self.table_widget._handle_process_ended(status_msg)

        if _error:
            QMessageBox.critical(
                self,
                _(_("Read Data Error")),
                _('An error occured while atempting to read data from<br>'
                  '<i>{}</i><br><br><font color="{}">{}:</font> {}')
                .format(self._filename, RED, type(_error).__name__, _error)
                )
            return

    def _update_table_model_data(self):
        """
        Format and update the data shown in the timeseries table.
        """
        if (self._file_reader is not None and
                self._file_reader.records is not None):
            dataf = self._file_reader.records.copy()
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

            # We round data to avoid decimals from round-off errors.
            for data_type in DataType:
                if data_type in dataf.columns:
                    dataf.loc[:, data_type] = (
                        dataf[data_type].round(decimals=6).copy())

            dataf_columns_mapper = [('datetime', _('Datetime'))]
            dataf_columns_mapper.extend([(dtype, dtype.label) for dtype in
                                         DataType if dtype in dataf.columns])
            self.table_model.set_model_data(dataf, dataf_columns_mapper)
        else:
            self.table_model.set_model_data(
                pd.DataFrame([]), dataf_columns_mapper=[])

    def _update_button_state(self):
        """Update the state of the dialog's buttons."""
        self.pathbox_widget.setEnabled(not self._data_is_loading)
        self.button_box.setEnabled(not self._data_is_loading)
        self.next_btn.setEnabled(len(self._queued_filenames) > 0)
        self.load_btn.setEnabled(self._obs_well_uuid is not None and
                                 not self._data_is_loaded and
                                 self.db_connection_manager.is_connected())
        self.show_data_btn.setEnabled(self._obs_well_uuid is not None)

    @Slot(QAbstractButton)
    def _handle_button_click_event(self, button):
        """
        Handle when a button is clicked on the dialog button box.
        """
        if button == self.close_btn:
            self.close()
        elif button == self.next_btn:
            self._load_next_queued_data_file()
        elif button == self.load_btn:
            if (self.pathbox_widget.is_enabled() and
                    not self.pathbox_widget.is_valid()):
                QMessageBox.warning(
                    self,
                    _("Invalid Directory"),
                    _("The directory specified for the option "
                      "<i>{}</i> is invalid.<br><br>"
                      "Please select a valid directory or uncheck "
                      "that option.").format(self.pathbox_widget.label)
                    )
                return
            self._save_imported_data_to_database()

    def _save_imported_data_to_database(self):
        """
        Save the data currently imported in this wizard in the database.
        """
        self.table_widget._start_process()
        self.table_widget.statusBar().showMessage(
            _('Saving data in the database...'))
        self.db_connection_manager.add_timeseries_data(
            self.tseries_dataf, self._obs_well_uuid, self._install_id,
            callback=self._handle_tseries_data_saved)
        self._data_is_loading = True
        self._update_button_state()

    @Slot()
    def _handle_tseries_data_saved(self):
        """
        Handle when tseries data were saved in the database.
        """
        self._data_is_loaded = True
        self._data_is_loading = False

        # Move input file if option is enabled and directory is valid.
        self._move_input_data_file()

        self.table_widget._end_process()
        self.table_widget.statusBar().showMessage(
            _('Data saved sucessfully in the database.'))
        self._update_button_state()

    def _move_input_data_file(self):
        """"
        Move input data file to the destination specified for the move input
        data file after loading option.
        """
        if (not self.pathbox_widget.is_enabled() or
                not self.pathbox_widget.is_valid()):
            return

        source_fpath = self._file_reader._file
        destination_fpath = osp.join(
            self.pathbox_widget.path(), osp.basename(source_fpath))
        if osp.samefile(osp.dirname(source_fpath),
                        osp.dirname(destination_fpath)):
            return

        # Ask user what to do if destination filepath aslready exist.
        if osp.exists(destination_fpath):
            msg_box = QMessageBox(
                QMessageBox.Question,
                _("Replace or Skip Moving Input File"),
                _("There is already a file named "
                  "<i>{}</i> in <i>{}</i>.<br><br>"
                  "Would you like to replace the file in "
                  "the destination or skip moving this input file?"
                  .format(osp.basename(destination_fpath),
                          osp.dirname(destination_fpath))
                  ),
                parent=self,
                buttons=QMessageBox.Yes | QMessageBox.No
                )
            msg_box.button(QMessageBox.Yes).setText('Replace')
            msg_box.button(QMessageBox.No).setText('Skip')
            answer = msg_box.exec_()
            if answer == QMessageBox.No:
                return

        # Move input file to destionation.
        try:
            replace_atomic(source_fpath, destination_fpath)
        except OSError:
            answer = QMessageBox.critical(
                self,
                _("Moving Input File Error"),
                _("Error moving <i>{}</i> to <i>{}</i>.<br><br>"
                  "Would you like to choose another location?")
                .format(osp.basename(self._file_reader._file),
                        self.pathbox_widget.path()),
                QMessageBox.Yes,
                QMessageBox.Cancel
                )
            if answer == QMessageBox.Yes:
                self.pathbox_widget.browse_path()
                self._move_input_data_file()

    def _view_timeseries_data(self):
        """
        Show the timeseries data that are already saved in the database
        for the observation well where the sonde related to this data file
        is installed.
        """
        if self._obs_well_uuid is not None:
            self.sig_view_data.emit(self._obs_well_uuid)

    # ---- Qt method override/extension
    def closeEvent(self, event):
        """Reimplement Qt closeEvent."""
        self._queued_filenames = []
        super().closeEvent(event)

    def show(self):
        """Reimplement Qt show."""
        if not len(self._queued_filenames):
            self._queued_filenames, _ = QFileDialog.getOpenFileNames(
                self.parent(), 'Select data files',
                self.working_directory, '*.csv ; *.lev ; *.xle')
        if len(self._queued_filenames):
            super().show()
            self._load_next_queued_data_file()


if __name__ == '__main__':
    from sardes.database.database_manager import DatabaseConnectionManager
    from sardes.database.accessor_demo import DatabaseAccessorDemo

    app = QApplication(sys.argv)

    dbconnmanager = DatabaseConnectionManager()
    dbconnmanager.connect_to_db(DatabaseAccessorDemo())

    dataimportwizard = DataImportWizard()
    dbconnmanager.register_model(
        dataimportwizard,
        'sondes_data',
        ['sonde_models_lib', 'sonde_installations',
         'observation_wells_data'])
    dataimportwizard._queued_filenames = [
        'C:/Users/User/sardes/sardes/plugins/dataio/'
        'tests/solinst_level_testfile.csv']
    dbconnmanager.update_model('data_import_wizard')

    dataimportwizard.show()

    sys.exit(app.exec_())
