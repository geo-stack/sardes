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
from sardes.database.accessors.accessor_sardes_lite import (
    DatabaseAccessorSardesLite)


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dbaccessor(tmp_path, obswells_data, repere_data, constructlog,
               readings_data):
    dbaccessor = DatabaseAccessorSardesLite(
        osp.join(tmp_path, 'sqlite_database_test.db'))
    dbaccessor.init_database()

    # Add observation wells.
    for obs_well_uuid, obs_well_data in obswells_data.iterrows():
        dbaccessor.add_observation_wells_data(
            obs_well_uuid, attribute_values=obs_well_data.to_dict())

        # Add a construction log.
        dbaccessor.set_construction_log(obs_well_uuid, constructlog)

        # Add timeseries data.
        dbaccessor.add_timeseries_data(
            readings_data, obs_well_uuid, install_uuid=None)

    # Add repere data to the database.
    for index, row in repere_data.iterrows():
        dbaccessor.add_repere_data(index, row.to_dict())

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
    Test that deleting data in a timeseries data table is working as
    expected.
    """
    publish_dialog = mainwindow.plugin.publish_dialog
    publish_dialog.setModal(False)
    qtbot.mouseClick(mainwindow.plugin.show_publish_dialog_btn, Qt.LeftButton)

    assert not publish_dialog.is_iri_data()
    assert not publish_dialog.is_iri_logs()
    assert not publish_dialog.is_iri_graphs()

    assert publish_dialog.iri_data() == ''
    assert publish_dialog.iri_logs() == ''
    assert publish_dialog.iri_graphs() == ''

    selectedfilename = osp.join(tmp_path, 'test_piezo_network.kml')
    selectedfilter = 'Keyhole Markup Language (*.kml)'
    mocker.patch.object(QFileDialog, 'getSaveFileName',
                        return_value=(selectedfilename, selectedfilter))

    # We then ask the manager to publish network to kml.
    with qtbot.waitSignal(mainwindow.plugin.sig_network_published,
                          timeout=5000):
        qtbot.mouseClick(publish_dialog.publish_button, Qt.LeftButton)
    qtbot.wait(150)


def test_publish_to_kml(mainwindow, qtbot, mocker, tmp_path):
    publish_dialog = mainwindow.plugin.publish_dialog
    publish_dialog.setModal(False)
    qtbot.mouseClick(mainwindow.plugin.show_publish_dialog_btn, Qt.LeftButton)

    # Now we check and define the IRIs for the file attachments.
    publish_dialog.iri_data_chbox.setChecked(True)
    publish_dialog.iri_logs_chbox.setChecked(True)
    publish_dialog.iri_graphs_chbox.setChecked(True)

    publish_dialog.iri_data_ledit.setText('http://www.tests_iri_data.ca')
    publish_dialog.iri_logs_ledit.setText('http://www.tests_iri_logs.ca')
    publish_dialog.iri_graphs_ledit.setText('http://www.tests_iri_graphs.ca')

    selectedfilename = osp.join(tmp_path, 'test_piezo_network2.kml')
    selectedfilter = 'Keyhole Markup Language (*.kml)'
    mocker.patch.object(QFileDialog, 'getSaveFileName',
                        return_value=(selectedfilename, selectedfilter))

    # We then ask the manager to publish network to kml.
    with qtbot.waitSignal(mainwindow.plugin.sig_network_published,
                          timeout=50000):
        qtbot.mouseClick(publish_dialog.publish_button, Qt.LeftButton)
    qtbot.wait(150)


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
