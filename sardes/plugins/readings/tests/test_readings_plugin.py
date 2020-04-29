# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the DatabaseConnectionWidget.
"""

# ---- Standard imports
import os
import os.path as osp
from unittest.mock import Mock
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMainWindow

# ---- Local imports
from sardes.database.database_manager import DatabaseConnectionManager
from sardes.database.accessor_demo import DatabaseAccessorDemo
from sardes.plugins.readings import SARDES_PLUGIN_CLASS
from sardes.widgets.tableviews import (MSEC_MIN_PROGRESS_DISPLAY, QMessageBox)


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dbconnmanager(qtbot):
    dbconnmanager = DatabaseConnectionManager()
    return dbconnmanager


@pytest.fixture
def mainwindow(qtbot, mocker, dbconnmanager):
    class MainWindowMock(QMainWindow):
        def __init__(self):
            super().__init__()
            self.panes_menu = Mock()
            self.db_connection_manager = dbconnmanager

            self.view_timeseries_data = Mock()
            self.plot_timeseries_data = Mock()

            self.plugin = SARDES_PLUGIN_CLASS(self)
            self.plugin.register_plugin()

    mainwindow = MainWindowMock()
    mainwindow.resize(1200, 750)
    mainwindow.show()
    qtbot.waitForWindowShown(mainwindow)
    qtbot.addWidget(mainwindow)

    with qtbot.waitSignal(dbconnmanager.sig_database_connected, timeout=3000):
        dbconnmanager.connect_to_db(DatabaseAccessorDemo())
    assert dbconnmanager.is_connected()
    qtbot.wait(1000)

    return mainwindow


# =============================================================================
# ---- Tests
# =============================================================================
def test_delete_timeseries_data(mainwindow, qtbot, mocker):
    """
    Test that deleting data in a timeseries data table is working as
    expected.

    Regression test for cgq-qgc/sardes#210
    """
    plugin = mainwindow.plugin
    plugin.view_timeseries_data(0)
    qtbot.waitUntil(lambda: len(plugin._tseries_data_tables) == 1)

    table = plugin._tseries_data_tables[0]
    qtbot.waitUntil(lambda: table.tableview.row_count() == 1826)
    assert table.isVisible()

    # Select one row in the table.
    model = table.model()
    selection_model = table.tableview.selectionModel()
    selection_model.setCurrentIndex(
        model.index(3, 0), selection_model.SelectCurrent)
    assert table.tableview.get_rows_intersecting_selection() == [3]
    assert table.tableview.delete_row_action.isEnabled()

    # Delete the selected row.
    table.tableview.delete_row_action.trigger()
    assert table.tableview.model().data_edit_count() == 1
    assert model.has_unsaved_data_edits() is True

    # Select more rows in the table.
    selection_model.select(model.index(1, 1), selection_model.Select)
    selection_model.select(model.index(4, 1), selection_model.Select)
    selection_model.select(model.index(5, 1), selection_model.Select)
    assert table.tableview.get_rows_intersecting_selection() == [1, 3, 4, 5]

    # Delete the selected rows.
    table.tableview.delete_row_action.trigger()
    assert model.data_edit_count() == 2
    assert model.has_unsaved_data_edits() is True

    # Commit the row deletions to the database.
    mocker.patch.object(QMessageBox, 'exec_', return_value=QMessageBox.Save)
    with qtbot.waitSignal(model.sig_data_updated, timeout=3000):
        table.tableview.save_edits_action.trigger()
    assert model.data_edit_count() == 0
    assert model.has_unsaved_data_edits() is False
    assert table.tableview.row_count() == 1826 - 4

    # Close the timeseries table.
    plugin.tabwidget.tabCloseRequested.emit(0)
    qtbot.waitUntil(lambda: len(plugin._tseries_data_tables) == 0)


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
