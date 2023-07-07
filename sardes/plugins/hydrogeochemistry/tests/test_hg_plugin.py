# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the Hydrogeochemistry plugin.
"""

# ---- Standard imports
import os
import os.path as osp
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFileDialog

# ---- Local imports
from sardes import __rootdir__
from sardes.app.mainwindow import MainWindowBase
from sardes.plugins.hydrogeochemistry import SARDES_PLUGIN_CLASS
from sardes.plugins.hydrogeochemistry.hgsurveys import HGSurveyImportManager
from sardes.database.database_manager import DatabaseConnectionWorker
from sardes.database.accessors.accessor_errors import ImportHGSurveysError


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def mainwindow(qtbot, mocker, dbaccessor):
    class MainWindow(MainWindowBase):
        def __init__(self):
            super().__init__()

        def setup_internal_plugins(self):
            self.plugin = SARDES_PLUGIN_CLASS(self)
            self.plugin.register_plugin()
            self.internal_plugins.append(self.plugin)

    mainwindow = MainWindow()
    mainwindow.show()
    qtbot.waitExposed(mainwindow)

    dbconnmanager = mainwindow.db_connection_manager
    with qtbot.waitSignal(dbconnmanager.sig_database_connected, timeout=3000):
        dbconnmanager.connect_to_db(dbaccessor)
    assert dbconnmanager.is_connected()

    qtbot.wait(1000)

    yield mainwindow

    # We need to wait for the mainwindow to close properly to avoid
    # runtime errors on the c++ side.
    with qtbot.waitSignal(mainwindow.sig_about_to_close):
        mainwindow.close()


# =============================================================================
# ---- Tests
# =============================================================================
def test_add_hg_survey_data(mainwindow, qtbot, mocker, dbaccessor):
    """
    Test that adding HG survey data imported from a XLSX file
    is working as expected.
    """
    manager = mainwindow.plugin.hgsurvey_import_manager
    dialog = manager.import_dialog
    dialog.setModal(False)
    qtbot.mouseClick(manager.show_import_dialog_btn, Qt.LeftButton)

    assert dialog.isVisible() is True
    assert dialog.import_btn.isEnabled() is False
    assert dialog.import_btn.isVisible()
    assert dialog.close_btn.isEnabled() is True
    assert dialog.close_btn.isVisible()
    assert dialog.input_file_pathbox.path() == ''

    # Select a input XLSX file.
    fpath = osp.join(
        __rootdir__, 'plugins', 'hydrogeochemistry', 'tests',
        'test_save_hgsurveys.xlsx')
    ffilter = "Excel Workbook (*.xlsx)"
    mocker.patch.object(
        QFileDialog, 'getOpenFileName', return_value=(fpath, ffilter)
        )

    qtbot.mouseClick(dialog.input_file_pathbox.browse_btn, Qt.LeftButton)
    assert dialog.import_btn.isEnabled() is True
    assert dialog.input_file_pathbox.path() == fpath

    # Import and add the data to the database.
    assert len(dbaccessor.get('hg_surveys')) == 4
    assert len(dbaccessor.get('purges')) == 3
    assert len(dbaccessor.get('hg_param_values')) == 4

    qtbot.mouseClick(dialog.import_btn, Qt.LeftButton)
    assert dialog._import_in_progress is True
    qtbot.waitUntil(lambda: dialog._import_in_progress is False)

    assert len(dbaccessor.get('hg_surveys')) == 4 + 1
    assert len(dbaccessor.get('purges')) == 3 + 5
    assert len(dbaccessor.get('hg_param_values')) == 4 + 3


def test_import_hg_survey_error(mainwindow, qtbot, mocker, dbaccessor):
    """
    Test that errors are displayed as expected when importing
    HG survey data.
    """
    manager = mainwindow.plugin.hgsurvey_import_manager
    dialog = manager.import_dialog
    dialog.setModal(False)
    qtbot.mouseClick(manager.show_import_dialog_btn, Qt.LeftButton)

    # Select a input XLSX file.
    fpath = osp.join(
        __rootdir__, 'plugins', 'hydrogeochemistry', 'tests',
        'test_save_hgsurveys.xlsx')
    dialog.input_file_pathbox.set_path(fpath)

    # Patch the HGSurveyImportManager to mock unsaved table changes.
    mocker.patch.object(
        HGSurveyImportManager,
        '_get_unsaved_tabletitles',
        return_value=(['Table#1, Table#2, Table #3'])
        )

    # Patch the DatabaseConnectionWorker to mock an import error.
    mocker.patch.object(
        DatabaseConnectionWorker,
        '_add_hg_survey_data',
        return_value=(ImportHGSurveysError('test_import_error', code=999),)
        )

    assert dialog.unsaved_changes_dialog.isVisible() is False
    assert dialog.import_error_dialog.isVisible() is False
    assert dialog.import_btn.isVisible() is True
    assert dialog.close_btn.isVisible() is True
    assert dialog.cancel_btn.isVisible() is False
    assert dialog.continue_btn.isVisible() is False
    assert dialog.ok_err_btn.isVisible() is False
    assert dialog.status_bar.status == dialog.status_bar.HIDDEN

    qtbot.mouseClick(dialog.import_btn, Qt.LeftButton)
    assert dialog.unsaved_changes_dialog.isVisible() is True
    assert dialog.import_error_dialog.isVisible() is False
    assert dialog.import_btn.isVisible() is False
    assert dialog.close_btn.isVisible() is False
    assert dialog.cancel_btn.isVisible() is True
    assert dialog.continue_btn.isVisible() is True
    assert dialog.ok_err_btn.isVisible() is False
    assert dialog.status_bar.status == dialog.status_bar.HIDDEN

    qtbot.mouseClick(dialog.continue_btn, Qt.LeftButton)
    assert dialog.unsaved_changes_dialog.isVisible() is False
    assert dialog.import_error_dialog.isVisible() is False
    assert dialog.import_btn.isVisible() is True
    assert dialog.close_btn.isVisible() is True
    assert dialog.cancel_btn.isVisible() is False
    assert dialog.continue_btn.isVisible() is False
    assert dialog.ok_err_btn.isVisible() is False
    assert dialog._import_in_progress is True
    assert dialog.status_bar.status == dialog.status_bar.IN_PROGRESS

    qtbot.waitUntil(lambda: dialog._import_in_progress is False)
    assert dialog.unsaved_changes_dialog.isVisible() is False
    assert dialog.import_error_dialog.isVisible() is True
    assert dialog.import_btn.isVisible() is False
    assert dialog.close_btn.isVisible() is False
    assert dialog.cancel_btn.isVisible() is False
    assert dialog.continue_btn.isVisible() is False
    assert dialog.ok_err_btn.isVisible() is True
    assert dialog.status_bar.status == dialog.status_bar.PROCESS_FAILED

    qtbot.mouseClick(dialog.ok_err_btn, Qt.LeftButton)
    assert dialog.unsaved_changes_dialog.isVisible() is False
    assert dialog.import_error_dialog.isVisible() is False
    assert dialog.import_btn.isVisible() is True
    assert dialog.close_btn.isVisible() is True
    assert dialog.cancel_btn.isVisible() is False
    assert dialog.continue_btn.isVisible() is False
    assert dialog.ok_err_btn.isVisible() is False

    # Patch the DatabaseConnectionWorker to mock a success.
    mocker.patch.object(
        DatabaseConnectionWorker,
        '_add_hg_survey_data',
        return_value=('test sucess import',)
        )

    qtbot.mouseClick(dialog.import_btn, Qt.LeftButton)
    qtbot.mouseClick(dialog.continue_btn, Qt.LeftButton)
    qtbot.waitUntil(lambda: dialog._import_in_progress is False)
    assert dialog.unsaved_changes_dialog.isVisible() is False
    assert dialog.import_error_dialog.isVisible() is False
    assert dialog.import_btn.isVisible() is True
    assert dialog.close_btn.isVisible() is True
    assert dialog.cancel_btn.isVisible() is False
    assert dialog.continue_btn.isVisible() is False
    assert dialog.ok_err_btn.isVisible() is False
    assert dialog.status_bar.status == dialog.status_bar.PROCESS_SUCCEEDED


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
