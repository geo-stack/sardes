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
import os.path as osp

# ---- Third party imports
import pytest
from qtpy.QtCore import Qt

# ---- Local imports
from sardes.database.accessor_demo import DatabaseAccessorDemo
from sardes.database.database_manager import DatabaseConnectionManager
from sardes.plugins.dataio.widgets.dataimportwizard import (
    QFileDialog, DataImportWizard, NOT_FOUND_MSG_COLORED)


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dbconnmanager(qtbot):
    dbconnmanager = DatabaseConnectionManager()
    with qtbot.waitSignal(dbconnmanager.sig_database_connected, timeout=3000):
        dbconnmanager.connect_to_db(DatabaseAccessorDemo())
    assert dbconnmanager.is_connected()
    qtbot.wait(100)
    return dbconnmanager


@pytest.fixture(scope="module")
def testdir():
    return osp.join(osp.dirname(__file__))


@pytest.fixture
def data_import_wizard(qtbot, dbconnmanager):
    data_import_wizard = DataImportWizard()
    qtbot.addWidget(data_import_wizard)

    dbconnmanager.register_model(
        data_import_wizard,
        'sondes_data',
        ['sonde_models_lib', 'sonde_installations', 'observation_wells_data'])
    with qtbot.waitSignal(data_import_wizard.sig_data_updated, timeout=3000):
        dbconnmanager.update_model('data_import_wizard')

    return data_import_wizard


# =============================================================================
# ---- Tests
# =============================================================================
def test_data_import_wizard_init(qtbot, mocker, testdir, data_import_wizard):
    """
    Test that the data import wizard imports and displays data
    as expected.
    """
    filenames = [osp.join(testdir, "solinst_level_testfile.csv"),
                 osp.join(testdir, "solinst_level_testfile.lev")]
    mocker.patch.object(QFileDialog, 'getOpenFileNames',
                        return_value=(filenames.copy(), ['.csv', '.lev']))
    data_import_wizard.show()

    # The first selected file is read automatically.
    assert data_import_wizard._queued_filenames == filenames[1:]
    assert data_import_wizard.working_directory == osp.dirname(filenames[-1])
    assert data_import_wizard.table_widget.tableview.row_count() == 100

    # Assert file infos.
    assert data_import_wizard.filename_label.text() == filenames[0]
    assert data_import_wizard.serial_number_label.text() == "1016042"
    assert data_import_wizard.projectid_label.text() == "03037041"
    assert (data_import_wizard.site_name_label.text() ==
            "SAINT-PAUL-D'ABBOTSFORD")

    # Assert sonde installation infos.
    assert (data_import_wizard.sonde_label.text() ==
            'Solinst LT M10 Gold 1016042')
    assert (data_import_wizard.obs_well_label.text() ==
            "03037041 (Saint-Paul-d'Abbotsford)")
    assert data_import_wizard.install_depth.text() == '9.02 m'
    assert (data_import_wizard.install_period.text() ==
            '2006-08-24 18:00 to ...')

    # Read the next selected file.
    qtbot.mouseClick(data_import_wizard.next_btn, Qt.LeftButton)
    assert data_import_wizard._queued_filenames == []
    assert data_import_wizard.working_directory == osp.dirname(filenames[-1])
    assert data_import_wizard.table_widget.tableview.row_count() == 100

    # Assert file infos.
    assert data_import_wizard.filename_label.text() == filenames[1]


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
