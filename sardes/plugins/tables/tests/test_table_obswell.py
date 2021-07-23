# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the Tables plugin.
"""

# ---- Standard imports
import datetime
import os
import os.path as osp
from unittest.mock import Mock
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pytest
from qtpy.QtCore import Qt, QUrl
from qtpy.QtGui import QDesktopServices

# ---- Local imports
from sardes.plugins.tables import SARDES_PLUGIN_CLASS
from sardes.widgets.tableviews import MSEC_MIN_PROGRESS_DISPLAY
from sardes.database.accessors import DatabaseAccessorSardesLite
from sardes.app.mainwindow import MainWindowBase


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
def tablewidget(qtbot, mocker, dbaccessor, obswells_data):
    class MainWindowMock(MainWindowBase):
        def __init__(self):
            self.view_timeseries_data = Mock()
            super().__init__()

        def setup_internal_plugins(self):
            self.plugin = SARDES_PLUGIN_CLASS(self)
            self.plugin.register_plugin()
            self.internal_plugins.append(self.plugin)

    mainwindow = MainWindowMock()
    mainwindow.show()
    qtbot.waitExposed(mainwindow)

    dbconnmanager = mainwindow.db_connection_manager
    with qtbot.waitSignal(dbconnmanager.sig_database_connected, timeout=3000):
        dbconnmanager.connect_to_db(dbaccessor)
    assert dbconnmanager.is_connected()

    # Select the tab corresponding to the observation wells table.
    tablewidget = mainwindow.plugin._tables['table_observation_wells']
    mainwindow.plugin.tabwidget.setCurrentWidget(tablewidget)
    qtbot.waitUntil(
        lambda: tablewidget.tableview.visible_row_count() == len(obswells_data)
        )
    qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)

    yield tablewidget

    # We need to wait for the mainwindow to close properly to avoid
    # runtime errors on the c++ side.
    with qtbot.waitSignal(mainwindow.sig_about_to_close):
        mainwindow.close()


# =============================================================================
# ---- Tests
# =============================================================================
def test_show_in_google_maps(tablewidget, qtbot, mocker):
    """
    Test that the tool to show the currently selected well in Google maps is
    working as expected.
    """
    tableview = tablewidget.tableview

    # We are selecting the first well in the table.
    tableview.set_current_index(0, 0)

    # We are patching QDesktopServices.openUrl because we don't want to
    # slow down tests by opening web pages on an external browser.
    patcher_qdesktopservices = mocker.patch.object(
        QDesktopServices, 'openUrl', return_value=True)
    tablewidget.show_in_google_maps()
    patcher_qdesktopservices.assert_called_once_with(QUrl(
        'https://www.google.com/maps/search/?api=1&query=45.445178,-72.828773'
        ))


def test_select_observation_well(tablewidget, qtbot, mocker, obswells_data):
    """
    Test that the UI state is as expected when selecting a new observation
    well.
    """
    tableview = tablewidget.tableview

    # We select the first well in the table and we assert that
    # the UI state is as expected.
    tableview.set_current_index(0, 0)

    assert not tablewidget.model().is_new_row_at(tableview.current_index())
    assert tablewidget.show_data_btn.isEnabled()
    assert tablewidget.construction_logs_manager.isEnabled()
    assert tablewidget.water_quality_reports.isEnabled()


def test_add_observation_well(tablewidget, qtbot, mocker, obswells_data,
                              dbaccessor):
    """
    Test that adding and selecting a new observation well is working as
    expected.
    """
    tableview = tablewidget.tableview

    # We add a new row and assert that the UI state is as expected.
    assert tableview.visible_row_count() == len(obswells_data)
    tableview.new_row_action.trigger()
    assert tableview.visible_row_count() == len(obswells_data) + 1

    assert tableview.model().is_new_row_at(tableview.current_index())
    assert not tablewidget.show_data_btn.isEnabled()
    assert not tablewidget.construction_logs_manager.isEnabled()
    assert not tablewidget.water_quality_reports.isEnabled()

    # Save the changes to the database.
    db_obswell_data = dbaccessor.get_observation_wells_data()
    assert len(db_obswell_data) == len(obswells_data)

    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    db_obswell_data = dbaccessor.get_observation_wells_data()
    assert len(db_obswell_data) == len(obswells_data) + 1


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
