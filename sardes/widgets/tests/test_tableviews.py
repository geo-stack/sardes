# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the ObservationWellTableView.
"""

# ---- Standard imports
import os.path as osp

# ---- Third party imports
import pytest
import pandas as pd
from pandas.testing import assert_frame_equal

# ---- Local imports
from sardes.config.locale import _
from sardes.database.database_manager import DatabaseConnectionManager
from sardes.widgets.tableviews import SardesTableView, SardesTableModel


TABLE_DATAF = pd.DataFrame(
    [['str1', True, 1.111, 1],
     ['str2', False, 2.222, 2],
     ['str3', True, 3.333, 3]],
    columns=['col1', 'col2', 'col3', 'col4']
    )


class MockSardesTableModel(SardesTableModel):
    __data_columns_mapper__ = [
        ('col1', _('Column #1')),
        ('col2', _('Column #2')),
        ('col3', _('Column #3')),
        ('col4', _('Column #4')),
        ]
    __get_data_method__ = 'get_data'


class MockDatabaseConnectionManager(DatabaseConnectionManager):
    def get_data(self, callback):
        callback(TABLE_DATAF)


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dbconnmanager():
    dbconnmanager = MockDatabaseConnectionManager()
    return dbconnmanager


@pytest.fixture
def tableview(qtbot, mocker, dbconnmanager):
    tableview = SardesTableView(MockSardesTableModel(dbconnmanager))
    tableview.show()
    qtbot.waitForWindowShown(tableview)
    qtbot.addWidget(tableview)

    # Setup the column options button.
    column_options_button = tableview.get_column_options_button()
    qtbot.addWidget(column_options_button)

    return tableview


# =============================================================================
# ---- Tests for ObservationWellTableView
# =============================================================================
def test_tableview_init(tableview, dbconnmanager, mocker, qtbot):
    """Test that the location table view is initialized correctly."""
    assert tableview
    assert tableview.model().rowCount() == 0
    assert tableview.model().columnCount() == len(TABLE_DATAF.columns)

    # Connect to the database. This should trigger in the location table view
    # a query to get and display the content of the database location table.
    dbconnmanager.sig_database_connection_changed.emit(True)

    # We need to wait a little to let the time for the data to display in
    # the table.
    qtbot.wait(1000)
    assert_frame_equal(tableview.source_model.dataf, TABLE_DATAF)

    # Assert that all columns are visible.
    for action in tableview._toggle_column_visibility_actions:
        assert action.isChecked()
    for logical_index in range(tableview.column_count()):
        assert not tableview.horizontalHeader().isSectionHidden(logical_index)


def test_toggle_column_visibility(tableview, qtbot):
    """Test toggling on and off the visibility of the columns."""
    horiz_header = tableview.horizontalHeader()
    assert tableview.column_count() == len(TABLE_DATAF.columns)
    assert tableview.visible_column_count() == len(TABLE_DATAF.columns)
    assert tableview.hidden_column_count() == 0

    # Hide the second, third, and fourth columns of the table.
    for logical_index in [1, 2, 3]:
        action = tableview._toggle_column_visibility_actions[logical_index]
        action.toggle()

        assert not action.isChecked()
        assert horiz_header.isSectionHidden(logical_index)
    assert tableview.hidden_column_count() == 3
    assert tableview.visible_column_count() == len(TABLE_DATAF.columns) - 3

    # Toggle back the visibility of the second column.
    action = tableview._toggle_column_visibility_actions[1]
    action.toggle()
    assert action.isChecked()
    assert not horiz_header.isSectionHidden(1)
    assert tableview.hidden_column_count() == 2
    assert tableview.visible_column_count() == len(TABLE_DATAF.columns) - 2

    # Restore column visibility with action 'Show all'.
    menu = tableview.get_column_options_button().menu()
    menu.actions()[1].trigger()
    for action in tableview._toggle_column_visibility_actions:
        assert action.isChecked()
    for logical_index in range(tableview.column_count()):
        assert not horiz_header.isSectionHidden(logical_index)
    assert tableview.visible_column_count() == len(TABLE_DATAF.columns)
    assert tableview.hidden_column_count() == 0


def test_restore_columns_to_defaults(tableview, qtbot):
    """Test restoring the visibility and order of the columns."""
    horiz_header = tableview.horizontalHeader()

    # Move the third column to first position.
    horiz_header.moveSection(2, 0)
    assert horiz_header.logicalIndex(0) == 2
    assert horiz_header.logicalIndex(2) == 1

    # Hide the second column.
    logical_index = 1
    action = tableview._toggle_column_visibility_actions[logical_index]
    action.toggle()
    assert not action.isChecked()
    assert horiz_header.isSectionHidden(logical_index)
    assert tableview.visible_column_count() == len(TABLE_DATAF.columns) - 1
    assert tableview.hidden_column_count() == 1

    # Restore columns to defaults with action 'Restore to defaults'.
    menu = tableview.get_column_options_button().menu()
    menu.actions()[0].trigger()
    assert horiz_header.logicalIndex(0) == 0
    assert horiz_header.logicalIndex(2) == 2
    assert action.isChecked()
    assert not horiz_header.isSectionHidden(logical_index)
    assert tableview.visible_column_count() == len(TABLE_DATAF.columns)
    assert tableview.hidden_column_count() == 0


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw', '-s'])
