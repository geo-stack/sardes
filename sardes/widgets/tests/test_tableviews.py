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
from copy import deepcopy
import os.path as osp
import uuid

# ---- Third party imports
import pytest
import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal
from qtpy.QtCore import Qt

# ---- Local imports
from sardes.config.locale import _
from sardes.widgets.tableviews import SardesTableView, SardesTableModel


NCOL = 5
COLUMNS = ['col{}'.format(i) for i in range(NCOL)]
HEADERS = [_('Column #{}').format(i) for i in range(NCOL)]
VALUES = [['str1', True, 1.111, 1],
          ['str2', False, 2.222, 2],
          ['str3', True, 3.333, 3]]
INDEXES = [uuid.uuid4() for i in range(len(VALUES))]
TABLE_DATAF = pd.DataFrame(
    VALUES,
    index=INDEXES,
    columns=COLUMNS[:-1]
    )
# Note that the fifth column mapped in the table model is
# missing in the dataframe.


class SardesTableModelMock(SardesTableModel):
    __data_columns_mapper__ = [
        (col, header) for col, header in zip(COLUMNS, HEADERS)]

    # ---- Public methods
    def fetch_model_data(self):
        self.set_model_data(deepcopy(TABLE_DATAF))

    def create_delegate_for_column(self, view, column):
        return None

    def save_value_change_edit(self, dataf_index, dataf_column, edited_value):
        TABLE_DATAF.loc[dataf_index, dataf_column] = edited_value


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def tablemodel(qtbot, mocker):
    tablemodel = SardesTableModelMock()
    return tablemodel


@pytest.fixture
def tableview(qtbot, mocker, tablemodel):
    tableview = SardesTableView(tablemodel)

    # Setup the width of the table so that all columns are shown.
    width = 0
    for i in range(tableview.column_count()):
        width += tableview.horizontalHeader().sectionSize(i)
    tableview.setMinimumWidth(width + 25)

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
def test_tableview_init(tableview, qtbot):
    """Test that the location table view is initialized correctly."""
    assert tableview
    assert tableview.model().rowCount() == 0
    assert tableview.model().columnCount() == NCOL
    assert tableview.visible_row_count() == 0

    # Fetch the model data. We need to wait a little to let the time for
    # the data to display in the table.
    tableview.model().fetch_model_data()
    assert_frame_equal(tableview.source_model.dataf, TABLE_DATAF)
    assert tableview.visible_row_count() == len(TABLE_DATAF)

    # Assert that all columns are visible.
    for action in tableview._toggle_column_visibility_actions:
        assert action.isChecked()
    for logical_index in range(tableview.column_count()):
        assert not tableview.horizontalHeader().isSectionHidden(logical_index)


def test_tableview_horiz_headers(tableview):
    """
    Test the labels of the table horizontal header.
    """
    for i, header in enumerate(HEADERS[:-1]):
        assert header == tableview.model().headerData(i, Qt.Horizontal)


def test_tableview_vert_headers(tableview, qtbot):
    """
    Test the labels of the table horizontal header.
    """
    tableview.model().fetch_model_data()
    assert tableview.visible_row_count() == len(TABLE_DATAF)
    for i in range(tableview.visible_row_count()):
        assert i + 1 == tableview.model().headerData(i, Qt.Vertical)
        assert (tableview.model().data(tableview.model().index(i, 0)) ==
                TABLE_DATAF.iloc[i, 0])

    # Sort rows along the first column.
    tableview.sortByColumn(0, Qt.DescendingOrder)
    for i in range(tableview.visible_row_count()):
        assert i + 1 == tableview.model().headerData(i, Qt.Vertical)
        assert (tableview.model().data(tableview.model().index(i, 0)) ==
                TABLE_DATAF.iloc[-1 - i, 0])


def test_tableview_row_selection(tableview, qtbot):
    """
    Test the data returned for the currently selected row.
    """
    tableview.model().fetch_model_data()
    assert tableview.get_selected_row_data() is None

    # Select the rows of table one after the other.
    for row in range(len(TABLE_DATAF)):
        index = tableview.proxy_model.index(row, 0)
        visual_rect = tableview.visualRect(index)
        qtbot.mouseClick(
            tableview.viewport(), Qt.LeftButton, pos=visual_rect.center())

        assert_frame_equal(tableview.get_selected_row_data(),
                           TABLE_DATAF.iloc[[row]])


def test_toggle_column_visibility(tableview, qtbot):
    """Test toggling on and off the visibility of the columns."""
    horiz_header = tableview.horizontalHeader()
    assert tableview.column_count() == NCOL
    assert tableview.visible_column_count() == NCOL
    assert tableview.hidden_column_count() == 0

    # Hide the second, third, and fourth columns of the table.
    for logical_index in [1, 2, 3]:
        action = tableview._toggle_column_visibility_actions[logical_index]
        action.toggle()

        assert not action.isChecked()
        assert horiz_header.isSectionHidden(logical_index)
    assert tableview.hidden_column_count() == 3
    assert tableview.visible_column_count() == NCOL - 3

    # Toggle back the visibility of the second column.
    action = tableview._toggle_column_visibility_actions[1]
    action.toggle()
    assert action.isChecked()
    assert not horiz_header.isSectionHidden(1)
    assert tableview.hidden_column_count() == 2
    assert tableview.visible_column_count() == NCOL - 2

    # Restore column visibility with action 'Show all'.
    menu = tableview.get_column_options_button().menu()
    menu.actions()[1].trigger()
    for action in tableview._toggle_column_visibility_actions:
        assert action.isChecked()
    for logical_index in range(tableview.column_count()):
        assert not horiz_header.isSectionHidden(logical_index)
    assert tableview.visible_column_count() == NCOL
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
    assert tableview.visible_column_count() == NCOL - 1
    assert tableview.hidden_column_count() == 1

    # Restore columns to defaults with action 'Restore to defaults'.
    menu = tableview.get_column_options_button().menu()
    menu.actions()[0].trigger()
    assert horiz_header.logicalIndex(0) == 0
    assert horiz_header.logicalIndex(2) == 2
    assert action.isChecked()
    assert not horiz_header.isSectionHidden(logical_index)
    assert tableview.visible_column_count() == NCOL
    assert tableview.hidden_column_count() == 0


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw', '-s'])
