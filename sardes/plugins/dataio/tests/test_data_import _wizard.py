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

# ---- Third party imports
import numpy as np
import pytest
from qtpy.QtCore import Qt

# ---- Local imports
from sardes.api.timeseries import DataType
from sardes.database.database_manager import DatabaseConnectionManager
from sardes.plugins.dataio.widgets.dataimportwizard import (
    QFileDialog, DataImportWizard, NOT_FOUND_MSG_COLORED, QMessageBox,
    SolinstFileReader)


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dbaccessor(qtbot):
    # We need to do this to make sure the demo database is reinitialized
    # after each test.
    try:
        del sys.modules['sardes.database.accessor_demo']
    except KeyError:
        pass
    from sardes.database.accessor_demo import DatabaseAccessorDemo
    return DatabaseAccessorDemo()


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
    filenames = ["solinst_level_testfile_03040002.csv"] * 2
    for filename in filenames:
        copyfile(osp.join(osp.dirname(__file__), filename),
                 osp.join(tmp_path, filename))
    return [osp.join(tmp_path, filename) for filename in filenames]


@pytest.fixture
def data_import_wizard(qtbot, dbconnmanager, testfiles, mocker):
    data_import_wizard = DataImportWizard()
    data_import_wizard.set_database_connection_manager(dbconnmanager)
    qtbot.addWidget(data_import_wizard)

    exts = [osp.splitext(file)[0] for file in testfiles]
    mocker.patch.object(
        QFileDialog, 'getOpenFileNames', return_value=(testfiles.copy(), exts))

    data_import_wizard.show()
    qtbot.waitForWindowShown(data_import_wizard)
    qtbot.waitUntil(lambda: data_import_wizard._is_updating is False,
                    timeout=3000)

    return data_import_wizard


# =============================================================================
# ---- Utilities
# =============================================================================
def assert_tseries_len(data_import_wizard, data_type, expected_length):
    """
    Fetch the tseries data from the database for the given observation
    well id and data type and assert that the legnth of the data is as
    expected.
    """
    tseries_data = (
        data_import_wizard.db_connection_manager.get_timeseries_for_obs_well(
            data_import_wizard._obs_well_uuid, [data_type],
            main_thread=True)
        )[0].get_merged_timeseries()
    assert len(tseries_data) == expected_length


# =============================================================================
# ---- Tests
# =============================================================================
def test_data_import_wizard_init(qtbot, mocker, testfiles, data_import_wizard):
    """
    Test that the data import wizard imports and displays data
    as expected.
    """
    # The first selected file is read automatically.
    assert data_import_wizard._queued_filenames == testfiles[1:]
    assert data_import_wizard.working_directory == osp.dirname(testfiles[-1])
    assert data_import_wizard.table_widget.tableview.row_count() == 365

    # Assert file infos.
    assert (data_import_wizard.filename_label.text() ==
            osp.basename(testfiles[0]))
    assert data_import_wizard.serial_number_label.text() == "1060487"
    assert data_import_wizard.projectid_label.text() == "03040002"
    assert (data_import_wizard.site_name_label.text() ==
            "Calixa-Lavallée")

    # Assert sonde installation infos.
    assert (data_import_wizard.sonde_label.text() ==
            'Solinst LT M10 1060487')
    assert (data_import_wizard.obs_well_label.text() ==
            "03040002 (Calixa-Lavallée)")
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
    assert data_import_wizard._queued_filenames == []
    assert data_import_wizard.working_directory == osp.dirname(testfiles[-1])
    assert data_import_wizard.table_widget.tableview.row_count() == 365

    # Assert file infos.
    assert (data_import_wizard.filename_label.text() ==
            osp.basename(testfiles[1]))


def test_read_data_error(qtbot, mocker, testfiles, data_import_wizard):
    """
    Test that the wizard is working as expected when there is an error
    while reading data from a file.
    """
    mocker.patch.object(
        SolinstFileReader, '__new__',
        side_effect=ValueError('Mocked error for test_read_data_error.'))
    patcher_msgbox_warning = mocker.patch.object(
        QMessageBox, 'critical', return_value=QMessageBox.Ok)

    # Read the next selected file.
    qtbot.mouseClick(data_import_wizard.next_btn, Qt.LeftButton)
    qtbot.waitUntil(lambda: data_import_wizard._is_updating is False)
    assert patcher_msgbox_warning.call_count == 1
    assert data_import_wizard.table_widget.tableview.row_count() == 0


def test_load_data(qtbot, mocker, testfiles, data_import_wizard):
    """
    Test that loading new timeseries data to the database is working as
    expected.
    """
    filename = testfiles[0]
    assert_tseries_len(data_import_wizard, DataType.WaterLevel, 1826)
    assert_tseries_len(data_import_wizard, DataType.WaterTemp, 1826)

    # We first try to load the data while setting an invalid directory for the
    # option to move the input data file after loading.
    data_import_wizard.pathbox_widget.checkbox.setChecked(True)
    data_import_wizard.pathbox_widget.set_path('some_non_valid_path')
    assert data_import_wizard.pathbox_widget.is_enabled()
    assert not data_import_wizard.pathbox_widget.is_valid()

    patcher_msgbox_warning = mocker.patch.object(
        QMessageBox, 'warning', return_value=QMessageBox.Ok)
    qtbot.mouseClick(data_import_wizard.save_btn, Qt.LeftButton)
    assert patcher_msgbox_warning.call_count == 1
    assert data_import_wizard._data_saved_in_database is False
    assert_tseries_len(data_import_wizard, DataType.WaterLevel, 1826)
    assert_tseries_len(data_import_wizard, DataType.WaterTemp, 1826)

    # We now disbaled the option to move the input data file after loading and
    # try to load the data again.
    data_import_wizard.pathbox_widget.checkbox.setChecked(False)
    assert data_import_wizard._data_saved_in_database is False
    qtbot.mouseClick(data_import_wizard.save_btn, Qt.LeftButton)
    qtbot.waitUntil(lambda: data_import_wizard._data_saved_in_database is True,
                    timeout=3000)
    assert patcher_msgbox_warning.call_count == 1
    assert_tseries_len(data_import_wizard, DataType.WaterLevel, 1826 + 365)
    assert_tseries_len(data_import_wizard, DataType.WaterTemp, 1826 + 365)
    assert osp.exists(filename)
    qtbot.wait(300)


@pytest.mark.parametrize('msgbox_answer', [QMessageBox.No, QMessageBox.Yes])
def test_move_input_file_if_exist(qtbot, mocker, data_import_wizard,
                                  msgbox_answer):
    """
    Test loading data when the option to move the input file to another
    destination is checked.
    """
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

    # We load the data.
    patcher_msgbox_exec_ = mocker.patch.object(
        QMessageBox, 'exec_', return_value=msgbox_answer)
    assert data_import_wizard._data_saved_in_database is False
    qtbot.mouseClick(data_import_wizard.save_btn, Qt.LeftButton)
    qtbot.waitUntil(lambda: data_import_wizard._data_saved_in_database is True,
                    timeout=3000)

    assert osp.exists(filename) is (msgbox_answer == QMessageBox.No)
    assert patcher_msgbox_exec_.call_count == 1
    assert_tseries_len(data_import_wizard, DataType.WaterLevel, 1826 + 365)
    assert_tseries_len(data_import_wizard, DataType.WaterTemp, 1826 + 365)
    qtbot.wait(1000)


def test_move_input_file_oserror(qtbot, mocker, data_import_wizard):
    """
    Test loading data when the operation to move the input data file fails.
    """
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
    assert_tseries_len(data_import_wizard, DataType.WaterLevel, 1826 + 365)
    assert_tseries_len(data_import_wizard, DataType.WaterTemp, 1826 + 365)

    assert data_import_wizard.pathbox_widget.path() == loaded_dirname_2
    assert osp.exists(osp.join(loaded_dirname_2, osp.basename(filename)))
    assert not osp.exists(filename)
    qtbot.wait(300)


def test_duplicate_readings(qtbot, mocker, data_import_wizard):
    """
    Test that duplicate readings are handled as expected by the wizard.
    """
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
    assert patcher_msgbox_exec_.call_count == 0
    assert_tseries_len(data_import_wizard, DataType.WaterLevel, 1826 + 365)
    assert_tseries_len(data_import_wizard, DataType.WaterTemp, 1826 + 365)

    assert data_import_wizard.datasaved_msgbox.isVisible()
    assert data_import_wizard._data_saved_in_database is True

    qtbot.wait(1000)
    qtbot.waitUntil(lambda: data_import_wizard._is_updating is False)
    assert np.sum(data_import_wizard._is_duplicated) == 365

    # # Close the "Data saved sucessfully" message box.
    # assert not data_import_wizard.duplicates_msgbox.isVisible()
    # data_import_wizard.datasaved_msgbox.close()
    # qtbot.wait(3000)
    # qtbot.waitUntil(lambda: data_import_wizard._is_updating is False)
    # assert not data_import_wizard.datasaved_msgbox.isVisible()
    # assert data_import_wizard.duplicates_msgbox.isVisible()


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
