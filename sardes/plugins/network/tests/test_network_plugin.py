# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the Readings plugin.
"""

# ---- Standard imports
import os
import os.path as osp
import sys
from unittest.mock import Mock
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pandas as pd
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFileDialog

# ---- Local imports
from sardes.app.mainwindow import MainWindowBase
from sardes.plugins.network import SARDES_PLUGIN_CLASS
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
    qtbot.waitForWindowShown(mainwindow)

    dbconnmanager = mainwindow.db_connection_manager
    with qtbot.waitSignal(dbconnmanager.sig_database_connected, timeout=3000):
        dbconnmanager.connect_to_db(dbaccessor)
    assert dbconnmanager.is_connected()
    qtbot.wait(150)

    yield mainwindow

    # We need to wait for the mainwindow to close properly to avoid
    # runtime errors on the c++ side.
    with qtbot.waitSignal(mainwindow.sig_about_to_close):
        mainwindow.close()


# =============================================================================
# ---- Tests
# =============================================================================
def test_publish_to_kml_nofiles(mainwindow, qtbot, mocker, tmp_path):
    """
    Test that publishing the piezometric network to KML when no
    attachment files are added is working as expected.
    """
    publish_dialog = mainwindow.plugin.publish_dialog
    publish_dialog.setModal(False)
    qtbot.mouseClick(mainwindow.plugin.show_publish_dialog_btn, Qt.LeftButton)

    assert not publish_dialog.is_iri_data()
    assert not publish_dialog.is_iri_logs()
    assert not publish_dialog.is_iri_graphs()
    assert not publish_dialog.is_iri_quality()

    assert publish_dialog.iri_data() == ''
    assert publish_dialog.iri_logs() == ''
    assert publish_dialog.iri_graphs() == ''
    assert publish_dialog.iri_quality() == ''

    selectedfilename = osp.join(tmp_path, 'test_piezo_network.kml')
    selectedfilter = 'Keyhole Markup Language (*.kml)'
    mocker.patch.object(QFileDialog, 'getSaveFileName',
                        return_value=(selectedfilename, selectedfilter))

    # We then ask the manager to publish network to kml.
    with qtbot.waitSignal(mainwindow.plugin.sig_network_published,
                          timeout=5000):
        qtbot.mouseClick(publish_dialog.publish_button, Qt.LeftButton)
    qtbot.wait(150)

    files_dirname = osp.join(tmp_path, 'test_piezo_network_files')
    path, dirs, files = next(os.walk(osp.join(files_dirname, 'data')))
    assert len(files) == 0
    path, dirs, files = next(os.walk(osp.join(files_dirname, 'diagrams')))
    assert len(files) == 0
    path, dirs, files = next(os.walk(osp.join(files_dirname, 'graphs')))
    assert len(files) == 0
    path, dirs, files = next(os.walk(osp.join(files_dirname, 'quality')))
    assert len(files) == 0


def test_publish_to_kml(mainwindow, qtbot, mocker, tmp_path,
                        obswells_data):
    """
    Test that publishing the piezometric network to KML is working as expected.
    """
    publish_dialog = mainwindow.plugin.publish_dialog
    publish_dialog.setModal(False)
    qtbot.mouseClick(mainwindow.plugin.show_publish_dialog_btn, Qt.LeftButton)

    # Now we check and define the IRIs for the file attachments.
    publish_dialog.iri_data_chbox.setChecked(True)
    publish_dialog.iri_logs_chbox.setChecked(True)
    publish_dialog.iri_graphs_chbox.setChecked(True)
    publish_dialog.iri_quality_chbox.setChecked(True)

    publish_dialog.iri_data_ledit.setText('http://www.tests_iri_data.ca')
    publish_dialog.iri_logs_ledit.setText('http://www.tests_iri_logs.ca')
    publish_dialog.iri_graphs_ledit.setText('http://www.tests_iri_graphs.ca')
    publish_dialog.iri_quality_ledit.setText('http://www.tests_iri_quality.ca')

    selectedfilename = osp.join(tmp_path, 'test_piezo_network.kml')
    selectedfilter = 'Keyhole Markup Language (*.kml)'
    mocker.patch.object(QFileDialog, 'getSaveFileName',
                        return_value=(selectedfilename, selectedfilter))

    # We then ask the manager to publish network to kml.
    with qtbot.waitSignal(mainwindow.plugin.sig_network_published,
                          timeout=50000):
        qtbot.mouseClick(publish_dialog.publish_button, Qt.LeftButton)
    qtbot.wait(150)

    files_dirname = osp.join(tmp_path, 'test_piezo_network_files')
    path, dirs, files = next(os.walk(osp.join(files_dirname, 'data')))
    assert len(files) == len(obswells_data)
    path, dirs, files = next(os.walk(osp.join(files_dirname, 'diagrams')))
    assert len(files) == len(obswells_data)
    path, dirs, files = next(os.walk(osp.join(files_dirname, 'graphs')))
    assert len(files) == len(obswells_data)
    path, dirs, files = next(os.walk(osp.join(files_dirname, 'quality')))
    assert len(files) == len(obswells_data)


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
