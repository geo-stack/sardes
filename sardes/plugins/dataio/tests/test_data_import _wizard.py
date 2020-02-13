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
from sardes.database.database_manager import DatabaseConnectionManager
from sardes.plugins.dataio.plugin import QFileDialog, DataImportWizard


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dbconnmanager(qtbot):
    dbconnmanager = DatabaseConnectionManager()
    return dbconnmanager


@pytest.fixture(scope="module")
def testdir():
    return osp.join(osp.dirname(__file__))


@pytest.fixture
def data_import_wizard(qtbot, dbconnmanager):
    data_import_wizard = DataImportWizard()
    qtbot.addWidget(data_import_wizard)

    dbconnmanager.register_model(
        data_import_wizard, 'sondes_data', ['sonde_models_lib'])

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

    assert data_import_wizard._queued_filenames == filenames[1:]
    assert data_import_wizard.working_directory == osp.dirname(filenames[-1])

    # The first selected file is read automatically.
    assert (data_import_wizard.filename_label.text() ==
            "solinst_level_testfile.csv")
    assert data_import_wizard.serial_number_label.text() == "1016042"
    assert data_import_wizard.project_id_label.text() == "03037041"
    assert (data_import_wizard.location_label.text() ==
            "SAINT-PAUL-D'ABBOTSFORD")
    assert data_import_wizard.model_label.text() == ''
    assert data_import_wizard.obs_well_label.text() == ''
    assert data_import_wizard.visit_date.text() == '2016-11-26 21:45:00'
    assert data_import_wizard.table_widget.tableview.row_count() == 300

    # Read the next selected file.
    qtbot.mouseClick(data_import_wizard.next_btn, Qt.LeftButton)
    assert data_import_wizard._queued_filenames == []
    assert data_import_wizard.working_directory == osp.dirname(filenames[-1])
    assert (data_import_wizard.filename_label.text() ==
            "solinst_level_testfile.lev")
    assert data_import_wizard.serial_number_label.text() == "1016042"
    assert data_import_wizard.project_id_label.text() == "03037041"
    assert (data_import_wizard.location_label.text() ==
            "SAINT-PAUL-D'ABBOTSFORD")
    assert data_import_wizard.model_label.text() == ''
    assert data_import_wizard.obs_well_label.text() == ''
    assert data_import_wizard.visit_date.text() == '2017-05-01 15:37:54'
    assert data_import_wizard.table_widget.tableview.row_count() == 300


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
