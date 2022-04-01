# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the DataImportWizard.
"""

# ---- Standard imports
import os
import os.path as osp
from shutil import copyfile
import sys
import datetime
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
from flaky import flaky
import pandas as pd
import numpy as np
import pytest
from qtpy.QtCore import Qt

# ---- Local imports
from sardes.api.timeseries import DataType
from sardes.database.database_manager import DatabaseConnectionManager
from sardes.plugins.dataio.widgets.dataimportwizard import (
    QFileDialog, DataImportWizard, QMessageBox, SolinstFileReader)
from sardes.database.accessors import DatabaseAccessorSardesLite


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dbaccessor(tmp_path, database_filler):
    dbaccessor = DatabaseAccessorSardesLite(
        osp.join(tmp_path, 'sqlite_database_test.db'))
    dbaccessor.init_database()
    database_filler(dbaccessor)

    return dbaccessor


@pytest.fixture
def dbconnmanager(qtbot, dbaccessor):
    dbconnmanager = DatabaseConnectionManager()
    with qtbot.waitSignal(dbconnmanager.sig_database_connected, timeout=3000):
        dbconnmanager.connect_to_db(dbaccessor)
    assert dbconnmanager.is_connected()
    qtbot.wait(100)
    return dbconnmanager


@pytest.fixture
def testfiles(tmp_path):
    filenames = ["solinst_level_testfile_03040002.csv",
                 "solinst_level_testfile_03040002.csv",
                 "solinst_conductivity_testfile.csv",
                 "solinst_duplicates_with_multiple_sondes.csv",
                 ]
    for filename in filenames:
        copyfile(osp.join(osp.dirname(__file__), filename),
                 osp.join(tmp_path, filename))
    return [osp.join(tmp_path, filename) for filename in filenames]


@pytest.fixture
def data_import_wizard(qtbot, dbconnmanager, testfiles, mocker):
    data_import_wizard = DataImportWizard()
    data_import_wizard.set_database_connection_manager(dbconnmanager)

    data_import_wizard.show()
    qtbot.waitExposed(data_import_wizard)

    assert len(data_import_wizard._queued_filenames) == 0
    assert not data_import_wizard.duplicates_msgbox.isVisible()
    assert not data_import_wizard.datasaved_msgbox.isVisible()

    yield data_import_wizard

    # We need to wait for the mainwindow to close properly to avoid
    # runtime errors on the c++ side.
    with qtbot.waitSignal(dbconnmanager.sig_database_disconnected):
        dbconnmanager.disconnect_from_db()
    data_import_wizard.close()


# =============================================================================
# ---- Utilities
# =============================================================================
def assert_tseries_len(data_import_wizard, data_type, expected_length):
    """
    Fetch the tseries data from the database for the given observation
    well id and data type and assert that the length of the data is as
    expected.
    """
    tseries_data = (
        data_import_wizard.db_connection_manager.get_timeseries_for_obs_well(
            data_import_wizard._obs_well_uuid, [data_type],
            main_thread=True)
        )
    assert len(tseries_data) == expected_length


# =============================================================================
# ---- Tests
# =============================================================================
def test_read_data(qtbot, mocker, testfiles, data_import_wizard):
    """
    Test that the data import wizard imports and displays data
    as expected.
    """
    tableview = data_import_wizard.table_widget.tableview

    # Select some files from the disk.
    exts = [osp.splitext(file)[0] for file in testfiles]
    mocker.patch.object(
        QFileDialog, 'getOpenFileNames', return_value=(testfiles.copy(), exts))
    qtbot.mouseClick(data_import_wizard.open_files_btn, Qt.LeftButton)
    qtbot.waitUntil(lambda: data_import_wizard._is_updating is False,
                    timeout=3000)

    # The first selected file is read automatically.
    assert data_import_wizard._queued_filenames == testfiles[1:]
    assert data_import_wizard.working_directory == osp.dirname(testfiles[-1])
    assert tableview.row_count() == 365
    assert tableview.visible_column_count() == 3
    assert DataType.WaterLevel in tableview.model().column_names()
    assert DataType.WaterTemp in tableview.model().column_names()

    # Assert file infos.
    assert (data_import_wizard.filename_label.text() ==
            osp.basename(testfiles[0]))
    assert data_import_wizard.serial_number_label.text() == "1060487"
    assert data_import_wizard.projectid_label.text() == "03040002"
    assert (data_import_wizard.site_name_label.text() ==
            "Calixa-Lavallée")

    # Assert sonde installation infos.
    assert data_import_wizard.sonde_label.text() == 'Solinst LT M10 1060487'
    assert data_import_wizard.obs_well_label.text() == '03040002 - PO-01'
    assert data_import_wizard.municipality_label.text() == 'Calixa-Lavallée'
    assert data_import_wizard.install_depth.text() == '9.24 m'
    assert (data_import_wizard.install_period.text() ==
            '2012-05-05 19:00 to today')

    # Assert internal variables values.
    data_import_wizard._sonde_serial_no = '1060487'
    data_import_wizard._obs_well_uuid = 4
    data_import_wizard._sonde_depth = 9.24
    data_import_wizard._install_id = 7

    # Read the next selected file.
    qtbot.mouseClick(data_import_wizard.next_btn, Qt.LeftButton)
    qtbot.waitUntil(lambda: data_import_wizard._is_updating is False)
    assert data_import_wizard._queued_filenames == testfiles[2:]
    assert data_import_wizard.working_directory == osp.dirname(testfiles[-1])
    assert tableview.row_count() == 365

    # Assert file infos.
    assert (data_import_wizard.filename_label.text() ==
            osp.basename(testfiles[1]))


def test_read_data_error(qtbot, mocker, testfiles, data_import_wizard):
    """
    Test that the wizard is working as expected when there is an error
    while reading data from a file.
    """
    # Patch SolinstFileReader to trigger an error when trying to read a file.
    mocker.patch.object(
        SolinstFileReader, '__new__',
        side_effect=ValueError('Mocked error for test_read_data_error.'))
    patcher_msgbox_warning = mocker.patch.object(
        QMessageBox, 'critical', return_value=QMessageBox.Ok)

    # Try to load data from an input data file and assert the mocked error
    # was shown as expected in a dialog.
    data_import_wizard._queued_filenames = testfiles
    data_import_wizard._load_next_queued_data_file()
    assert patcher_msgbox_warning.call_count == 1
    assert data_import_wizard.table_widget.tableview.row_count() == 0


def test_update_when_db_changed(qtbot, mocker, testfiles, data_import_wizard):
    """
    Test that the wizard updating as expected when changes are made to the
    database.

    Regression test for cgq-qgc/sardes#266
    """
    table_model = data_import_wizard.table_model

    # Load the data from an inut data file.
    data_import_wizard._queued_filenames = testfiles
    data_import_wizard._load_next_queued_data_file()
    qtbot.waitUntil(lambda: data_import_wizard._is_updating is False,
                    timeout=3000)

    # Assert sonde installation infos.
    assert data_import_wizard.sonde_label.text() == 'Solinst LT M10 1060487'
    assert data_import_wizard.obs_well_label.text() == '03040002 - PO-01'
    assert data_import_wizard.municipality_label.text() == 'Calixa-Lavallée'
    assert data_import_wizard.install_depth.text() == '9.24 m'
    assert (data_import_wizard.install_period.text() ==
            '2012-05-05 19:00 to today')
    assert table_model.get_value_at(table_model.index(0, 1)) == 2.062441

    # Change the installation depth in the database.
    installation_id = data_import_wizard._install_id
    dbconnmanager = data_import_wizard.db_connection_manager
    with qtbot.waitSignal(dbconnmanager.sig_database_data_changed):
        dbconnmanager.set(
            'sonde_installations', installation_id, {'install_depth': 10.24})
    qtbot.waitUntil(lambda: data_import_wizard._is_updating is False)

    assert data_import_wizard.install_depth.text() == '10.24 m'
    assert data_import_wizard._sonde_depth == 10.24
    assert table_model.get_value_at(table_model.index(0, 1)) == 3.062441

    # Change the name and municipality of the well.
    with qtbot.waitSignal(dbconnmanager.sig_database_data_changed):
        dbconnmanager.set(
            'observation_wells_data',
            data_import_wizard._obs_well_uuid,
            {'obs_well_id': '12340002',
             'municipality': 'New Municipality Name'})
    qtbot.waitUntil(lambda: data_import_wizard._is_updating is False)
    assert data_import_wizard.obs_well_label.text() == '12340002 - PO-01'
    assert (data_import_wizard.municipality_label.text() ==
            'New Municipality Name')


def test_save_data_to_database(qtbot, mocker, testfiles, data_import_wizard,
                               readings_data):
    """
    Test that saving new timeseries data to the database is working as
    expected.
    """
    len_readings = len(readings_data)

    # Load the data from an inut data file.
    data_import_wizard._queued_filenames = testfiles
    data_import_wizard._load_next_queued_data_file()
    qtbot.waitUntil(lambda: data_import_wizard._is_updating is False,
                    timeout=3000)

    assert_tseries_len(data_import_wizard, DataType.WaterLevel, len_readings)
    assert_tseries_len(data_import_wizard, DataType.WaterTemp, len_readings)

    # We first try to load the data while setting an invalid directory for the
    # option to move the input data file after loading.
    data_import_wizard.pathbox_widget.set_enabled(True)
    data_import_wizard.pathbox_widget.set_path('some_non_valid_path')
    assert data_import_wizard.pathbox_widget.is_enabled()
    assert not data_import_wizard.pathbox_widget.is_valid()

    patcher_msgbox_warning = mocker.patch.object(
        QMessageBox, 'warning', return_value=QMessageBox.Ok)
    qtbot.mouseClick(data_import_wizard.save_btn, Qt.LeftButton)
    assert patcher_msgbox_warning.call_count == 1
    assert data_import_wizard._data_saved_in_database is False
    assert_tseries_len(data_import_wizard, DataType.WaterLevel, len_readings)
    assert_tseries_len(data_import_wizard, DataType.WaterTemp, len_readings)

    # We now disbaled the option to move the input data file after loading and
    # try to load the data again.
    data_import_wizard.pathbox_widget.checkbox.setChecked(False)
    assert data_import_wizard._data_saved_in_database is False
    qtbot.mouseClick(data_import_wizard.save_btn, Qt.LeftButton)
    qtbot.waitUntil(lambda: data_import_wizard._data_saved_in_database is True,
                    timeout=3000)
    assert patcher_msgbox_warning.call_count == 1
    assert_tseries_len(
        data_import_wizard, DataType.WaterLevel, len_readings + 365)
    assert_tseries_len(
        data_import_wizard, DataType.WaterTemp, len_readings + 365)
    assert osp.exists(testfiles[0])
    qtbot.wait(300)


@pytest.mark.parametrize('msgbox_answer', [QMessageBox.No, QMessageBox.Yes])
def test_move_input_file_if_exist(qtbot, mocker, data_import_wizard,
                                  msgbox_answer, testfiles, readings_data):
    """
    Test loading data when the option to move the input file to another
    destination is checked.
    """
    # Load the data from an inut data file.
    data_import_wizard._queued_filenames = testfiles
    data_import_wizard._load_next_queued_data_file()
    qtbot.waitUntil(lambda: data_import_wizard._is_updating is False,
                    timeout=3000)

    filename = data_import_wizard.filename
    testdir = osp.dirname(filename)

    # Set a valid destination for the option to move input files after
    # loading data.
    loaded_dirname = osp.join(testdir, 'loaded_datafiles')
    os.makedirs(loaded_dirname)
    data_import_wizard.pathbox_widget.checkbox.setChecked(True)
    data_import_wizard.pathbox_widget.set_path(loaded_dirname)
    assert data_import_wizard.pathbox_widget.is_enabled()
    assert data_import_wizard.pathbox_widget.is_valid()

    # We create an new empty file in the destination folder with the same name
    # as that of the input file to trigger a "Replace or Skip Moving
    # Input File" message.
    with open(osp.join(loaded_dirname, osp.basename(filename)), "w") as f:
        f.write("")
    assert osp.exists(osp.join(loaded_dirname, osp.basename(filename)))

    # We load the data in the database.
    patcher_msgbox_exec_ = mocker.patch.object(
        QMessageBox, 'exec_', return_value=msgbox_answer)
    assert data_import_wizard._data_saved_in_database is False
    qtbot.mouseClick(data_import_wizard.save_btn, Qt.LeftButton)
    qtbot.waitUntil(lambda: data_import_wizard._data_saved_in_database is True,
                    timeout=3000)

    assert osp.exists(filename) is (msgbox_answer == QMessageBox.No)
    assert patcher_msgbox_exec_.call_count == 1

    assert_tseries_len(
        data_import_wizard, DataType.WaterLevel, len(readings_data) + 365)
    assert_tseries_len(
        data_import_wizard, DataType.WaterTemp, len(readings_data) + 365)

    qtbot.wait(1000)


def test_move_input_file_oserror(qtbot, mocker, data_import_wizard, testfiles,
                                 readings_data):
    """
    Test loading data when the operation to move the input data file fails.
    """
    # Load the data from an inut data file.
    data_import_wizard._queued_filenames = testfiles
    data_import_wizard._load_next_queued_data_file()
    qtbot.waitUntil(lambda: data_import_wizard._is_updating is False,
                    timeout=3000)

    filename = data_import_wizard.filename
    testdir = osp.dirname(filename)

    # Set a valid destination for the option to move input files after
    # loading data.
    loaded_dirname = osp.join(testdir, 'loaded_datafiles')
    os.makedirs(loaded_dirname)
    loaded_dirname_2 = osp.join(testdir, 'loaded_datafiles_2')
    os.makedirs(loaded_dirname_2)
    data_import_wizard.pathbox_widget.checkbox.setChecked(True)
    data_import_wizard.pathbox_widget.set_path(loaded_dirname)

    # We open a file with the same name as that of the input file in the
    # destination folder so that the operation to move the input file fails
    opened_fname = open(osp.join(loaded_dirname, osp.basename(filename)), "w")

    # We must patch the dialogs to simulate user inputs.
    patcher_msgbox_exec_ = mocker.patch.object(
        QMessageBox, 'exec_', return_value=QMessageBox.Yes)
    patcher_msgbox_warning = mocker.patch.object(
        QMessageBox, 'critical', return_value=QMessageBox.Yes)
    patcher_qfiledialog = mocker.patch.object(
        QFileDialog, 'getExistingDirectory', return_value=(loaded_dirname_2))

    # We now load the data.
    assert data_import_wizard._data_saved_in_database is False
    qtbot.mouseClick(data_import_wizard.save_btn, Qt.LeftButton)
    qtbot.waitUntil(lambda: data_import_wizard._data_saved_in_database is True,
                    timeout=3000)

    assert patcher_msgbox_exec_.call_count == 1
    assert patcher_msgbox_warning.call_count == 1
    assert patcher_qfiledialog.call_count == 1
    assert_tseries_len(
        data_import_wizard, DataType.WaterLevel, len(readings_data) + 365)
    assert_tseries_len(
        data_import_wizard, DataType.WaterTemp, len(readings_data) + 365)

    assert data_import_wizard.pathbox_widget.path() == loaded_dirname_2
    assert osp.exists(osp.join(loaded_dirname_2, osp.basename(filename)))
    assert not osp.exists(filename)
    qtbot.wait(300)


@flaky(max_runs=3)
def test_duplicate_readings(qtbot, mocker, data_import_wizard, testfiles,
                            readings_data):
    """
    Test that duplicate readings are handled as expected by the wizard.
    """
    # Load the data from an input data file.
    data_import_wizard._queued_filenames = testfiles.copy()
    data_import_wizard._load_next_queued_data_file()
    qtbot.waitUntil(lambda: data_import_wizard._is_updating is False,
                    timeout=3000)

    # Patch the message box that appears to warn ask the user to confirm
    # adding duplicate data to the database.
    patcher_msgbox_exec_ = mocker.patch.object(
        QMessageBox, 'exec_', return_value=QMessageBox.Yes)
    data_import_wizard.pathbox_widget.checkbox.setChecked(False)

    # Save the data to the database.
    assert np.sum(data_import_wizard._is_duplicated) == 0
    assert not data_import_wizard.datasaved_msgbox.isVisible()
    with qtbot.waitSignal(
            data_import_wizard.db_connection_manager.sig_tseries_data_changed,
            timeout=3000):
        qtbot.mouseClick(data_import_wizard.save_btn, Qt.LeftButton)
    qtbot.waitUntil(lambda: data_import_wizard._is_updating is False)

    assert patcher_msgbox_exec_.call_count == 0
    assert_tseries_len(
        data_import_wizard, DataType.WaterLevel, len(readings_data) + 365)
    assert_tseries_len(
        data_import_wizard, DataType.WaterTemp, len(readings_data) + 365)
    assert data_import_wizard._data_saved_in_database is True
    assert data_import_wizard.datasaved_msgbox.isVisible()
    assert np.sum(data_import_wizard._is_duplicated) == 365
    assert not data_import_wizard.duplicates_msgbox.isVisible()
    assert not data_import_wizard.save_btn.isEnabled()

    # Assert that the "Previous" and "Next" button are working as
    # expected in the "duplicates_msgbox".
    assert (data_import_wizard.table_widget.current_data() ==
            '2019-01-01 00:00:00')

    # Go to "Next" duplicate value.
    qtbot.mouseClick(
        data_import_wizard.duplicates_msgbox.buttons[1], Qt.LeftButton)
    assert (data_import_wizard.table_widget.current_data() ==
            '2019-01-02 00:00:00')

    # Go to "Previous" duplicate value.
    qtbot.mouseClick(
        data_import_wizard.duplicates_msgbox.buttons[0], Qt.LeftButton)
    assert (data_import_wizard.table_widget.current_data() ==
            '2019-01-01 00:00:00')

    # Close the "Data saved sucessfully" message box.
    data_import_wizard.datasaved_msgbox.close()
    assert not data_import_wizard.datasaved_msgbox.isVisible()
    assert not data_import_wizard.duplicates_msgbox.isVisible()
    assert not data_import_wizard.save_btn.isEnabled()
    assert data_import_wizard._data_saved_in_database is True

    # Load the data from the save file a second time.
    data_import_wizard._queued_filenames = testfiles.copy()
    data_import_wizard._load_next_queued_data_file()
    qtbot.waitUntil(lambda: data_import_wizard._is_updating is False)

    assert data_import_wizard._data_saved_in_database is False
    assert not data_import_wizard.datasaved_msgbox.isVisible()
    assert data_import_wizard.duplicates_msgbox.isVisible()
    assert data_import_wizard.save_btn.isEnabled()
    assert np.sum(data_import_wizard._is_duplicated) == 365

    # Save the data again to the database.
    with qtbot.waitSignal(
            data_import_wizard.db_connection_manager.sig_tseries_data_changed,
            timeout=3000):
        qtbot.mouseClick(data_import_wizard.save_btn, Qt.LeftButton)
    qtbot.waitUntil(lambda: data_import_wizard._is_updating is False)

    assert patcher_msgbox_exec_.call_count == 1
    assert_tseries_len(
        data_import_wizard, DataType.WaterLevel, len(readings_data) + 730)
    assert_tseries_len(
        data_import_wizard, DataType.WaterTemp, len(readings_data) + 730)

    assert data_import_wizard._data_saved_in_database is True
    assert data_import_wizard.datasaved_msgbox.isVisible()
    assert not data_import_wizard.duplicates_msgbox.isVisible()
    assert not data_import_wizard.save_btn.isEnabled()


def test_read_conductivity_data(qtbot, mocker, data_import_wizard, testfiles):
    """
    Test that conductivity data are read and displayed as expected.
    """
    # Load the data from an inut data file.
    data_import_wizard._queued_filenames = testfiles[2:]
    data_import_wizard._load_next_queued_data_file()
    qtbot.waitUntil(lambda: data_import_wizard._is_updating is False)

    tableview = data_import_wizard.table_widget.tableview
    assert tableview.row_count() == 10
    assert tableview.visible_column_count() == 4
    assert DataType.WaterEC in tableview.model().column_names()


def test_duplicates_with_multiple_sondes(
        qtbot, mocker, data_import_wizard, testfiles):
    """
    Test that checking for duplicate values for a well equipped with more
    than one synchroneous sondes is working as expected.

    Regression test for cgq-qgc/sardes#266
    Regression test for cgq-qgc/sardes#392
    """
    dbmanager = data_import_wizard.db_connection_manager

    # We mock the data stored in the dabase to simulate a well equiped
    # with more than one synchroneous sondes installed at different depths.
    merged_data = pd.DataFrame(
        [['2018-09-27 07:00:00', None, None, None, '1073744'],
         ['2018-09-27 08:00:00', None, None, None, '1073744'],
         ['2018-09-27 11:00:00', None, None, None, '1073744'],
         ['2018-09-27 07:00:00', None, None, None, '1073747'],
         ['2018-09-27 09:00:00', None, None, None, '1073747'],
         ],
        columns=['datetime', DataType.WaterLevel, DataType.WaterTemp,
                 DataType.WaterEC, 'sonde_id'])
    merged_data['datetime'] = pd.to_datetime(
        merged_data['datetime'], format="%Y-%m-%d %H:%M:%S")
    mocker.patch.object(dbmanager._worker,
                        '_get_timeseries_for_obs_well',
                        return_value=(merged_data,))

    sonde_installation = pd.Series(
        {'sampling_feature_uuid': 0,
         'sonde_uuid': 9,
         'start_date': datetime.datetime(2018, 9, 27, 7, 0),
         'end_date': None,
         'install_depth': 10.25,
         'well_municipality': "Saint-Paul-d'Abbotsford",
         'sonde_brand_model': 'Solinst LTC M100 Edge',
         'well_common_name': 'Saint-Paul',
         'well_name': '03037041'})
    mocker.patch.object(dbmanager._worker,
                        '_get_sonde_installation_info',
                        return_value=(sonde_installation,))

    # We select an input data files associated with sonde 1073744
    # and assert that the duplicated values are flagged as expected.
    data_import_wizard._queued_filenames = testfiles[3:]
    data_import_wizard._load_next_queued_data_file()
    qtbot.waitUntil(lambda: data_import_wizard._is_updating is False)

    # We assert that the information shown in the wizard were updated as
    # expected.
    assert data_import_wizard._sonde_serial_no == '1073744'
    assert (data_import_wizard.sonde_label.text() ==
            'Solinst LTC M100 Edge 1073744')
    assert data_import_wizard.obs_well_label.text() == "03037041 - Saint-Paul"
    assert (data_import_wizard.municipality_label.text() ==
            "Saint-Paul-d'Abbotsford")
    assert data_import_wizard.install_depth.text() == '10.25 m'
    assert (data_import_wizard.install_period.text() ==
            '2018-09-27 07:00 to today')

    assert np.sum(data_import_wizard._is_duplicated) == 3


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
