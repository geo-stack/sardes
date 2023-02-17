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
    from sardes.widgets.tableviews import SardesTableView
    from sardes.api.tablemodels import SardesTableColumn


# ---- Standard imports
import sys
import os.path as osp

# ---- Third party imports
from appconfigs.base import get_home_dir
from atomicwrites import replace_atomic
from hydsensread import SolinstFileReader
import numpy as np
import pandas as pd
from qtpy.QtCore import Qt, Slot, Signal
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QApplication, QFileDialog, QLabel, QFormLayout, QGroupBox, QMessageBox,
    QGridLayout, QFrame, QStackedWidget, QCheckBox, QWidget)

# ---- Local imports
from sardes.config.gui import get_iconsize, RED, YELLOWLIGHT
from sardes.config.locale import _
from sardes.api.panes import SardesPaneWidget
from sardes.api.tablemodels import SardesTableModel, SardesTableColumn
from sardes.api.timeseries import DataType
from sardes.utils.qthelpers import create_toolbutton
from sardes.widgets.tableviews import SardesTableWidget
from sardes.tables.delegates import NotEditableDelegate
from sardes.widgets.path import CheckboxPathBoxWidget
from sardes.widgets.statusbar import MessageBoxWidget

NOT_FOUND_MSG = _('Not found in database')
NOT_FOUND_MSG_COLORED = '<font color=red>%s</font>' % NOT_FOUND_MSG
READ_ERROR_MSG = _('File reading error')
READ_ERROR_MSG_COLORED = '<font color=red>%s</font>' % READ_ERROR_MSG


class ImportDataTableModel(SardesTableModel):
    is_duplicated = None
    highlight_duplicates = False

    __tablecolumns__ = (
        [SardesTableColumn(
            'datetime', _('Datetime'), 'datetime64[ns]')] +
        [SardesTableColumn(
            dtype, dtype.label, 'float64') for dtype in DataType]
        )

    def create_delegate_for_column(self, table_view: SardesTableView,
                                   table_column: SardesTableColumn):
        delegate = NotEditableDelegate(table_view, table_column)
        self._column_delegates[table_column.name] = delegate
        return delegate

    def set_duplicated(self, is_duplicated):
        self.is_duplicated = is_duplicated
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.rowCount() - 1, self.columnCount() - 1)
            )

    # ---- SardesTableModel overrides
    def data(self, index, role=Qt.DisplayRole):
        """Qt method override."""
        if role == Qt.BackgroundRole and self.is_duplicated is not None:
            if self.is_duplicated[index.row()]:
                return QColor(YELLOWLIGHT)
        return super().data(index, role)


class DataImportWizard(SardesPaneWidget):
    sig_view_data = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_('Data Import Wizard'))
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.resize(575, 600)

        # A flag to indicate whether data is currently being loaded in the
        # database.
        self._loading_data_in_database = False
        # A flag to indicate if the date were saved in the database during
        # the current sesstion.
        self._data_saved_in_database = False
        # A flag to indicate whether this data import wizard is being updated.
        self._is_updating = True
        # A flag to indicate whether a confirmation message should be shown
        # before saving potential duplicates in the database.
        self._confirm_before_saving_duplicates = True

        self._file_reader = None
        self._working_dir = get_home_dir()
        self._queued_filenames = []
        self._file_count = 0
        self._file_current_index = 0

        # An array of boolean values that indicate, for each reading of the
        # imported data, whether data is already saved in the database for
        # the corresponding sonde.
        self._is_duplicated = None

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
        file_layout.addRow(_('Input File:'), self.filename_label)
        file_layout.addRow(_('Project ID:'), self.projectid_label)
        file_layout.addRow(_('Location:'), self.site_name_label)
        file_layout.addRow(_('Serial Number:'), self.serial_number_label)

        # Setup sonde installation info groupbox.
        self.sonde_label = QLabel()
        obs_well_fieldname = QLabel(_('Well:'))
        obs_well_fieldname.setAlignment(Qt.AlignTop)
        self.obs_well_label = QLabel()
        self.obs_well_label.setWordWrap(True)
        municipality_fieldname = QLabel(_('Municipality:'))
        municipality_fieldname.setAlignment(Qt.AlignTop)
        self.municipality_label = QLabel()
        self.municipality_label.setWordWrap(True)
        self.install_depth = QLabel()
        self.install_period = QLabel()

        sonde_info_widget = QFrame()
        sonde_form = QGridLayout(sonde_info_widget)
        sonde_form.setContentsMargins(0, 0, 0, 0)
        sonde_form.addWidget(QLabel(_('Sonde:')), 0, 0)
        sonde_form.addWidget(self.sonde_label, 0, 1)
        sonde_form.addWidget(obs_well_fieldname, 1, 0)
        sonde_form.addWidget(self.obs_well_label, 1, 1)
        sonde_form.addWidget(municipality_fieldname, 2, 0)
        sonde_form.addWidget(self.municipality_label, 2, 1)
        sonde_form.addWidget(QLabel(_('Depth:')), 3, 0)
        sonde_form.addWidget(self.install_depth, 3, 1)
        sonde_form.addWidget(QLabel(_('Period:')), 4, 0)
        sonde_form.addWidget(self.install_period, 4, 1)
        sonde_form.setRowStretch(sonde_form.rowCount(), 1)
        sonde_form.setColumnStretch(1, 1)

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

        # Setup previous data groupbox.
        self.previous_date_label = QLabel()
        self.previous_level_label = QLabel()
        self.delta_level_label = QLabel()
        self.delta_date_label = QLabel()

        previous_widget = QFrame()
        previous_layout = QGridLayout(previous_widget)
        previous_layout.addWidget(QLabel(_('Previous Date:')), 0, 0)
        previous_layout.addWidget(self.previous_date_label, 0, 1)
        previous_layout.addWidget(QLabel(_('Delta Date:')), 1, 0)
        previous_layout.addWidget(self.delta_date_label, 1, 1)
        previous_layout.addWidget(
            QLabel(_('Previous Water Level:')), 2, 0)
        previous_layout.addWidget(self.previous_level_label, 2, 1)
        previous_layout.addWidget(
            QLabel(_('Delta Water Level:')), 3, 0)
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
        table_widget = self._setup_table()

        # Setup the pathbox widget for the 'move file' feature.
        self.pathbox_widget = CheckboxPathBoxWidget(
            label=_('Move the input file to this location after loading data'))
        pathbox_groupbox = QFrame()
        pathbox_layout = QGridLayout(pathbox_groupbox)
        pathbox_layout.setContentsMargins(0, 10, 0, 10)
        pathbox_layout.addWidget(self.pathbox_widget)
        table_widget.central_widget.layout().addWidget(
            pathbox_groupbox, 4, 0, 1, 2)

        # Setup toolbar.
        upper_toolbar = self.get_upper_toolbar()
        self.open_files_btn = create_toolbutton(
            self,
            icon='browse_files',
            text=_("Open File"),
            tip=_("Select one or more input data files from which time data "
                  "is to be imported."),
            triggered=self._browse_files,
            shortcut='Ctrl+O',
            iconsize=get_iconsize()
            )
        upper_toolbar.addWidget(self.open_files_btn)

        self.save_btn = create_toolbutton(
            self,
            icon='save_to_db',
            text=_("Save to Database"),
            tip=_("Save the currently imported time data to the database."),
            triggered=self._save_data_to_database,
            iconsize=get_iconsize()
            )
        upper_toolbar.addWidget(self.save_btn)

        # We add the copy action from the table widget to this wizard toolbar.
        upper_toolbar.addAction(
            self.table_widget.get_upper_toolbar().actions()[0])

        upper_toolbar.addSeparator()
        self.file_count_label = QLabel(' {} of {}'.format(
            self._file_current_index, self._file_count))
        upper_toolbar.addWidget(self.file_count_label)

        self.next_btn = create_toolbutton(
            self,
            icon='file_next',
            text=_("Load Next File"),
            tip=_("Load the time data of the next selected file."),
            triggered=self._load_next_queued_data_file,
            iconsize=get_iconsize()
            )
        upper_toolbar.addWidget(self.next_btn)
        upper_toolbar.addSeparator()

        # We now add the remaining actions from the table widget toolbar
        # to this wizard toolbar.
        for action in self.table_widget.get_upper_toolbar().actions()[2:]:
            upper_toolbar.addAction(action)
        self.table_widget.get_upper_toolbar().clear()
        self.table_widget.get_upper_toolbar().hide()
        upper_toolbar.addSeparator()

        self.show_data_btn = create_toolbutton(
            self,
            icon='show_data_table',
            text=_("View data"),
            tip=_('Show the data of the timeseries acquired in the currently '
                  'selected observation well in a table.'),
            triggered=lambda _: self._view_timeseries_data(),
            iconsize=get_iconsize()
            )
        upper_toolbar.addWidget(self.show_data_btn)

        # Setup the layout.
        central_widget = QWidget()
        layout = QGridLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(file_groupbox, 1, 0, 1, 2)
        layout.addWidget(sonde_groupbox, 2, 0)
        layout.addWidget(previous_groupbox, 2, 1)
        layout.addWidget(table_widget, 3, 0, 1, 2)
        layout.setRowStretch(3, 1)

        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)

        self.set_central_widget(central_widget)

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
        self.db_connection_manager.sig_tseries_data_changed.connect(
            self._handle_tseries_data_changed)
        self.db_connection_manager.sig_database_data_changed.connect(
            self._handle_database_data_changed)

    def _handle_database_connection_changed(self, connected):
        """
        Handle when the connection to the database change.
        """
        self._update()

    def _handle_tseries_data_changed(self, sampling_feature_uuids):
        """
        Handle when timeseries data changed in the database.
        """
        if self._obs_well_uuid in sampling_feature_uuids:
            self._update_button_state(is_updating=True)
            self._update_previous_data()

    def _handle_database_data_changed(self, data_names):
        """
        Handle when data needed by this wizard changed in the database.
        """
        for name in data_names:
            if name in ['sondes_data', 'sonde_installations',
                        'observation_wells_data', 'sonde_models_lib']:
                self._update()
                break

    # ---- Message boxes
    def _setup_message_boxes(self):
        """
        Setup a warning box that shows when data already exists
        in the database for the data and sonde serial number related to the
        imported data.
        """
        self.duplicates_msgbox = self.table_widget.install_message_box(
            MessageBoxWidget(color=YELLOWLIGHT, icon='warning'))
        prev_button = self.duplicates_msgbox.add_button(_('Previous'))
        prev_button.clicked.connect(
            lambda _: self.goto_closest_duplicate(direction='previous'))
        next_button = self.duplicates_msgbox.add_button(_('Next'))
        next_button.clicked.connect(
            lambda _: self.goto_closest_duplicate(direction='next'))

        self.duplicates_msgbox.sig_closed.connect(
            lambda: self.table_model.set_duplicated(None))

        self.datasaved_msgbox = self.table_widget.install_message_box(
            MessageBoxWidget(color='#E5FFCC', icon='succes'))
        self.datasaved_msgbox.set_message(
            _('Data saved sucessfully in the database.'))

    def _update_duplicated_satus(self):
        """
        Update the duplicate warning text and status as well as the table
        duplicate highlighting data.
        """
        is_duplicated = (
            None if self._data_saved_in_database else self._is_duplicated)
        nbr_duplicated = (
            0 if is_duplicated is None else np.sum(is_duplicated))

        self.table_model.set_duplicated(is_duplicated)
        if nbr_duplicated == 0:
            self.duplicates_msgbox.hide()
        else:
            self.duplicates_msgbox.set_message(_(
                "Data for {} of these readings was found in the database."
                ).format(nbr_duplicated))
            self.duplicates_msgbox.show()
        self._update_button_state(is_updating=False)

    def goto_closest_duplicate(self, direction):
        """
        Go to the next duplicate reading in the table when direction is 'next'
        and go to the previous one when it is 'previous'.
        """
        tableview = self.table_widget.tableview
        tableview.setFocus()
        current_index = tableview.currentIndex()

        sorted_duplicated = pd.Series(self._is_duplicated.values[
            tableview.model()._map_row_from_source])
        duplicated_rows = sorted_duplicated.index[sorted_duplicated.values]
        if direction == 'next':
            try:
                goto_row = duplicated_rows[
                    duplicated_rows > current_index.row()][0]
            except IndexError:
                goto_row = duplicated_rows[0]
        elif direction == 'previous':
            try:
                goto_row = duplicated_rows[
                    duplicated_rows < current_index.row()][-1]
            except IndexError:
                goto_row = duplicated_rows[-1]

        tableview.selectionModel().setCurrentIndex(
            tableview.model().index(goto_row, current_index.column()),
            tableview.selectionModel().ClearAndSelect)

    # ---- Table
    def clear_table(self):
        """
        Clear the content of the table.
        """
        horizontal_header = self.table_widget.tableview.horizontalHeader()
        for section in range(horizontal_header.count()):
            horizontal_header.setSectionHidden(section, True)
        self.table_model.set_model_data(pd.DataFrame([]))

    def _setup_table(self):
        """
        Setup the table model and widget used to display the imported data
        in this wizard.
        """
        self.table_model = ImportDataTableModel()
        self.table_widget = SardesTableWidget(
            self.table_model, multi_columns_sort=False,
            sections_movable=False, sections_hidable=False,
            disabled_actions=SardesTableWidget.EDIT_ACTIONS,
            statusbar=True)
        self._setup_message_boxes()

        # Setup the horizontal header.
        horizontal_header = self.table_widget.tableview.horizontalHeader()
        horizontal_header.setDefaultSectionSize(125)
        self.clear_table()

        return self.table_widget

    def _update_table_model_data(self):
        """
        Format and update the data shown in the timeseries table.
        """
        horiz_header = self.table_widget.tableview.horizontalHeader()
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
                elif column.lower().startswith('conduct'):
                    dataf.rename(columns={column: DataType.WaterEC},
                                 inplace=True)

            horiz_header.setSectionHidden(0, False)
            for data_type in DataType:
                if data_type in dataf.columns:
                    # We round data to avoid decimals from round-off errors.
                    dataf.loc[:, data_type] = (
                        dataf[data_type].round(decimals=6).copy())

                # We hide or show the corresponding column in the table.
                horiz_header.setSectionHidden(
                    self.table_model.column_names().index(data_type),
                    data_type not in dataf.columns)

            self.table_model.set_model_data(dataf)
        else:
            self.clear_table()
        self._update_previous_data()

    # ---- Private API
    def _update(self):
        """
        Update the content of this data import wizard.
        """
        self._update_button_state(is_updating=True)
        self._update_installation_info()
        # Calling the above method will trigger this sequence of calls in
        # this data import data wizard :
        # _update_installation_info -> _set_installation_info ->
        # _update_table_model_data -> _update_previous_data ->
        # _set_previous_data -> _update_duplicated_satus ->
        # _update_button_state

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
            self.municipality_label.clear()
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
            self.obs_well_label.setText('{} - {}'.format(
                sonde_install_data['well_name'],
                sonde_install_data['well_common_name'],
                ))
            self.municipality_label.setText(
                sonde_install_data['well_municipality']
                )
            self.install_depth.setText('{} m'.format(
                str(sonde_install_data['install_depth'])
                ))
            self.install_period.setText(_('{} to {}').format(
                sonde_install_data['start_date'].strftime("%Y-%m-%d %H:%M"),
                _('today') if pd.isnull(sonde_install_data['end_date']) else
                sonde_install_data['end_date'].strftime("%Y-%m-%d %H:%M")
                ))
            self.sonde_stacked_widget.setCurrentIndex(0)
        else:
            self.sonde_label.setText(NOT_FOUND_MSG_COLORED)
            self.obs_well_label.setText(NOT_FOUND_MSG_COLORED)
            self.municipality_label.setText(NOT_FOUND_MSG_COLORED)
            self.install_depth.setText(NOT_FOUND_MSG_COLORED)
            self.install_period.setText(NOT_FOUND_MSG_COLORED)
            self.sonde_stacked_widget.setCurrentIndex(0)
        self._update_table_model_data()

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
        self.previous_date_label.clear()
        self.previous_level_label.clear()
        self.delta_level_label.clear()
        self.delta_date_label.clear()
        self.previous_stacked_widget.setCurrentIndex(0)
        self._update_duplicated_satus()

    def _set_previous_data(self, prev_dataf):
        """
        Set the information regarding the water level reading that is
        stored in the database previous to the data series contained in
        the data file.
        """
        self._is_duplicated = None
        if self._file_reader is None:
            self._clear_previous_data()
            return
        if not self.db_connection_manager.is_connected():
            self.previous_msg_label.setText(
                _('Info not available because not connected to a database.'))
            self.previous_stacked_widget.setCurrentIndex(1)
            self._update_duplicated_satus()
            return
        if prev_dataf is None:
            self._clear_previous_data()
            return

        new_dataf = self.tseries_dataf
        if (DataType.WaterLevel not in prev_dataf.columns or
                DataType.WaterLevel not in new_dataf.columns):
            self._clear_previous_data()
            return

        # Update Previous Data Info.
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
        else:
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

        # Check for duplicates.
        in_db = (prev_dataf[['datetime', 'sonde_id']]
                 .drop_duplicates())
        to_add = new_dataf[['datetime']].copy()
        to_add['sonde_id'] = self._sonde_serial_no

        # See https://stackoverflow.com/a/50645338/4481445
        self._is_duplicated = to_add.apply(tuple, 1).isin(
            in_db.apply(tuple, 1))

        self._update_duplicated_satus()

    def _load_next_queued_data_file(self):
        """
        Load the data from the next file in the queue.
        """
        self._file_current_index += 1
        self.file_count_label.setText(' {} of {}'.format(
            self._file_current_index, self._file_count))
        self.datasaved_msgbox.hide()
        self.table_widget._start_process(_('Loading data...'))
        self._data_saved_in_database = False
        self._filename = self._queued_filenames.pop(0)
        self.working_directory = osp.dirname(self._filename)
        self.filename_label.setText(osp.basename(self._filename))
        self.filename_label.setToolTip(self._filename)
        self._update_button_state(is_updating=True)
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
            status_msg = _('Data imported sucessfully from the file.')
        self._update_installation_info()
        self.table_widget._handle_process_ended(status_msg)

        if _error:
            QMessageBox.critical(
                self,
                _("Read Data Error"),
                _('An error occured while atempting to read data from<br>'
                  '<i>{}</i><br><br><font color="{}">{}:</font> {}'
                  ).format(self._filename, RED, type(_error).__name__, _error)
                )
            return

    def _update_button_state(self, is_updating=None):
        """
        Update the state of the dialog's buttons.

        Parameters
        ----------
        is_updating: bool
            Whether the data import wizard is being updated.
        """
        if is_updating is not None:
            self._is_updating = is_updating

        self.show_data_btn.setEnabled(self._obs_well_uuid is not None)
        self.pathbox_widget.setEnabled(not self._loading_data_in_database and
                                       not self._is_updating)
        if self._loading_data_in_database or self._is_updating:
            self.open_files_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
        else:
            self.open_files_btn.setEnabled(True)
            self.next_btn.setEnabled(len(self._queued_filenames) > 0)
            self.save_btn.setEnabled(
                self._obs_well_uuid is not None and
                self.db_connection_manager.is_connected() and
                not self._data_saved_in_database)

    def _save_data_to_database(self):
        """
        Save the imported data to the database.
        """
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

        nbr_duplicated = (
            0 if self._is_duplicated is None else np.sum(self._is_duplicated))
        if nbr_duplicated > 0 and self._confirm_before_saving_duplicates:
            msg_box = QMessageBox(
                QMessageBox.Question,
                _("Confirm Dulicates Saving"),
                _("This operation will potentially add {} duplicate "
                  "readings to the database.<br><br>"
                  "Are you sure you want to continue?<br><br>"
                  ).format(nbr_duplicated),
                parent=self,
                buttons=QMessageBox.Yes | QMessageBox.No)

            chkbox = QCheckBox(
                _("Do not show this message again during this session."))
            msg_box.setCheckBox(chkbox)

            answer = msg_box.exec_()
            self._confirm_before_saving_duplicates = not chkbox.isChecked()
            if answer == QMessageBox.No:
                self.table_model.set_duplicated(self._is_duplicated)
                self.duplicates_msgbox.show()
                return

        self.table_widget._start_process()
        self.table_widget.statusBar().showMessage(
            _('Saving data to the database...'))
        self._loading_data_in_database = True
        self.db_connection_manager.add_timeseries_data(
            self.tseries_dataf, self._obs_well_uuid, self._install_id,
            callback=self._handle_data_saved_in_database)
        self._update_button_state()

    @Slot()
    def _handle_data_saved_in_database(self):
        """
        Handle when the imported data were saved in the database.
        """
        self._data_saved_in_database = True
        self._loading_data_in_database = False
        self.duplicates_msgbox.close()
        self.datasaved_msgbox.show()

        # Move input file if option is enabled and directory is valid.
        self._move_input_data_file()

        self.table_widget._end_process()
        self.table_widget.statusBar().showMessage(
            _('Data saved sucessfully in the database.'))

        self._update_button_state(is_updating=False)

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
                  ).format(osp.basename(destination_fpath),
                           osp.dirname(destination_fpath)),
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

    def _browse_files(self):
        """
        Opend a Qt file dialog to select input data files.
        """
        filenames = QFileDialog.getOpenFileNames(
            self.parent(), 'Select data files',
            self.working_directory, '*.csv ; *.lev ; *.xle')[0]
        if filenames:
            self._file_count = len(filenames)
            self._file_current_index = 0
            self._queued_filenames = filenames
            self._load_next_queued_data_file()

    # ---- Qt method override/extension
    def closeEvent(self, event):
        """Reimplement Qt closeEvent."""
        self._file_count = 0
        self._file_current_index = 0
        self._queued_filenames = []
        super().closeEvent(event)


if __name__ == '__main__':
    from sardes.database.database_manager import DatabaseConnectionManager
    from sardes.database.accessors import DatabaseAccessorSardesLite

    app = QApplication(sys.argv)

    database = "D:/Desktop/rsesq_prod_21072020_v1.db"
    dbconnmanager = DatabaseConnectionManager()
    dbconnmanager.connect_to_db(DatabaseAccessorSardesLite(database))

    dataimportwizard = DataImportWizard()
    dataimportwizard.set_database_connection_manager(dbconnmanager)
    dataimportwizard._queued_filenames = [
        'C:/Users/User/sardes/sardes/plugins/dataio/'
        'tests/solinst_level_testfile_03040002.csv']
    dataimportwizard.show()

    sys.exit(app.exec_())
