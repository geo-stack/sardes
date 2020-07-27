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
import sys
from unittest.mock import Mock
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMainWindow

# ---- Local imports
from sardes.database.database_manager import DatabaseConnectionManager
from sardes.plugins.readings import SARDES_PLUGIN_CLASS
from sardes.widgets.tableviews import (MSEC_MIN_PROGRESS_DISPLAY, QMessageBox)


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
def dbconnmanager(qtbot):
    dbconnmanager = DatabaseConnectionManager()
    return dbconnmanager


@pytest.fixture
def mainwindow(qtbot, mocker, dbconnmanager, dbaccessor):
    class MainWindowMock(QMainWindow):
        def __init__(self):
            super().__init__()
            self.panes_menu = Mock()
            self.db_connection_manager = dbconnmanager

            self.view_timeseries_data = Mock()
            self.plot_timeseries_data = Mock()

            self.register_table = Mock()
            self.unregister_table = Mock()

            self.plugin = SARDES_PLUGIN_CLASS(self)
            self.plugin.register_plugin()

    mainwindow = MainWindowMock()
    mainwindow.resize(1200, 750)
    mainwindow.show()
    qtbot.waitForWindowShown(mainwindow)
    qtbot.addWidget(mainwindow)

    with qtbot.waitSignal(dbconnmanager.sig_database_connected, timeout=3000):
        dbconnmanager.connect_to_db(dbaccessor)
    assert dbconnmanager.is_connected()
    qtbot.wait(1000)

    # Show data for observation well #1.
    mainwindow.plugin.view_timeseries_data(0)
    qtbot.waitUntil(lambda: len(mainwindow.plugin._tseries_data_tables) == 1)

    # Wait until the data are loaded in the table.
    table = mainwindow.plugin._tseries_data_tables[0]
    qtbot.waitUntil(lambda: table.tableview.row_count() == 1826)
    assert table.isVisible()

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
    table = mainwindow.plugin._tseries_data_tables[0]

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
    # assert table.tableview.row_count() == 1826 - 4

    # Close the timeseries table.
    mainwindow.plugin.tabwidget.tabCloseRequested.emit(0)
    qtbot.waitUntil(lambda: len(mainwindow.plugin._tseries_data_tables) == 0)


def test_edit_then_delete_row(mainwindow, qtbot, mocker):
    """
    Test that editing and then deleting data on a same row is working as
    expected.

    Regression test for cgq-qgc/sardes#337
    """
    table = mainwindow.plugin._tseries_data_tables[0]

    # Edit a cell on the second row of the table.
    model_index = table.model().index(2, 2)
    assert table.model().get_value_at(model_index) == 3.210969794207334
    edited_value = 999.99
    table.model().set_data_edit_at(model_index, edited_value)
    assert table.model().get_value_at(model_index) == 999.99
    assert table.model().data_edit_count() == 1

    # Delete the secon row of the table.
    table.model().delete_row([2])
    assert table.model().data_edit_count() == 2

    # Commit the edits to the database.
    mocker.patch.object(QMessageBox, 'exec_', return_value=QMessageBox.Save)
    with qtbot.waitSignal(table.model().sig_data_updated, timeout=3000):
        table.tableview.save_edits_action.trigger()

    model_index = table.model().index(2, 2)
    assert table.model().get_value_at(model_index) == 3.2786624267542765

    assert table.tableview.row_count() == 1826 - 1


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
