# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the SardesTableWidget class.
"""

# ---- Standard imports
from copy import deepcopy
import os.path as osp
import uuid

# ---- Third party imports
import pytest
import pandas as pd
from pandas.testing import assert_frame_equal
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication

# ---- Local imports
from sardes.config.locale import _
from sardes.widgets.tableviews import (
    SardesTableWidget, SardesTableModel, NotEditableDelegate,
    StringEditDelegate, NumEditDelegate, BoolEditDelegate, QMessageBox)


# =============================================================================
# ---- Fixtures
# =============================================================================
NCOL = 6
COLUMNS = ['col{}'.format(i) for i in range(NCOL)]
HEADERS = [_('Column #{}').format(i) for i in range(NCOL)]
VALUES = [['str1', True, 1.111, 3, 'not editable'],
          ['str2', False, 2.222, 1, 'not editable'],
          ['str3', True, 3.333, 2, 'not editable']]
INDEXES = [uuid.uuid4() for i in range(len(VALUES))]


@pytest.fixture
def TABLE_DATAF():
    # Note that the sixth column mapped in the table model is
    # missing in the dataframe.
    return pd.DataFrame(
        VALUES,
        index=INDEXES,
        columns=COLUMNS[:-1]
        )


@pytest.fixture
def tablemodel(qtbot, TABLE_DATAF):
    class SardesTableModelMock(SardesTableModel):
        __data_columns_mapper__ = [
            (col, header) for col, header in zip(COLUMNS, HEADERS)]

        # ---- Public methods
        def fetch_model_data(self, *args, **kargs):
            self.set_model_data(deepcopy(TABLE_DATAF))

        def create_delegate_for_column(self, view, column):
            if column == 'col0':
                return StringEditDelegate(view, unique_constraint=True,
                                          is_required=True)
            elif column == 'col1':
                return BoolEditDelegate(view)
            elif column == 'col2':
                return NumEditDelegate(view, decimals=3)
            elif column == 'col3':
                return NumEditDelegate(view)
            else:
                return NotEditableDelegate(view)

        def save_data_edits(self):
            """
            Save all data edits to the database.
            """
            for edits in self._dataf_edits:
                for edit in edits:
                    if edit.type() == self.ValueChanged:
                        TABLE_DATAF.loc[edit.dataf_index,
                                        edit.dataf_column] = edit.edited_value
            self.fetch_model_data()

    tablemodel = SardesTableModelMock()
    return tablemodel


@pytest.fixture
def tablewidget(qtbot, tablemodel):
    tablewidget = SardesTableWidget(tablemodel)

    # Setup the width of the table so that all columns are shown.
    width = 0
    for i in range(tablewidget.tableview.column_count()):
        width += tablewidget.tableview.horizontalHeader().sectionSize(i)
    tablewidget.tableview.setMinimumWidth(width + 25)

    tablewidget.show()
    qtbot.waitForWindowShown(tablewidget)
    qtbot.addWidget(tablewidget)

    # Assert everything is working as expected when table is empty.
    assert tablewidget
    assert tablewidget.tableview.model().rowCount() == 0
    assert tablewidget.tableview.model().columnCount() == NCOL
    assert tablewidget.tableview.visible_row_count() == 0

    # Fetch the model data explicitely. We need to do this because
    # the table view that we use for testing is not connected to a
    # database connection manager.
    tablewidget.tableview.model().fetch_model_data()
    qtbot.wait(100)

    return tablewidget


# =============================================================================
# ---- Utils
# =============================================================================
def get_values_for_column(model_index):
    """
    Return the list of displayed values in the column of the table
    corresponding to the specified model index.
    """
    model = model_index.model()
    column = model_index.column()
    return [
        model.index(row, column).data() for row in range(model.rowCount())]


# =============================================================================
# ---- Tests
# =============================================================================
def test_tablewidget_init(tablewidget, TABLE_DATAF):
    """Test that SardesTableWidget is initialized correctly."""
    tableview = tablewidget.tableview
    horiz_header = tablewidget.tableview.horizontalHeader()
    model = tableview.model()

    # Assert that the content of the table is as expected.
    assert_frame_equal(tableview.source_model.dataf, TABLE_DATAF)
    assert tableview.visible_row_count() == len(TABLE_DATAF)

    # Assert that all columns are visible.
    for action in tableview.get_column_visibility_actions():
        assert action.isChecked()
    for logical_index in range(tableview.column_count()):
        assert not tableview.horizontalHeader().isSectionHidden(logical_index)

    # Assert that no column is initially selected.
    assert tableview.get_selected_columns() == []

    # Assert that the data are not initially sorted.
    assert get_values_for_column(model.index(0, 0)) == ['str1', 'str2', 'str3']
    assert horiz_header.sortIndicatorOrder() == 0
    assert horiz_header.sortIndicatorSection() == -1


def test_tablewidget_horiz_headers(tablewidget):
    """
    Test the labels of the table horizontal header.
    """
    tableview = tablewidget.tableview
    for i, header in enumerate(HEADERS[:-1]):
        assert header == tableview.model().headerData(i, Qt.Horizontal)


def test_tablewidget_vert_headers(tablewidget, TABLE_DATAF):
    """
    Test the labels of the table horizontal header.
    """
    tableview = tablewidget.tableview
    assert tableview.visible_row_count() == len(TABLE_DATAF)
    for i in range(tableview.visible_row_count()):
        assert i + 1 == tableview.model().headerData(i, Qt.Vertical)
        assert (tableview.model().data(tableview.model().index(i, 0)) ==
                TABLE_DATAF.iloc[i, 0])

    # Sort rows along the first column.
    tableview.sort_by_column(0, Qt.DescendingOrder)
    for i in range(tableview.visible_row_count()):
        assert i + 1 == tableview.model().headerData(i, Qt.Vertical)
        assert (tableview.model().data(tableview.model().index(i, 0)) ==
                TABLE_DATAF.iloc[-1 - i, 0])


def test_tablewidget_row_selection(tablewidget, qtbot, TABLE_DATAF):
    """
    Test the data returned for the currently selected row.
    """
    tableview = tablewidget.tableview
    assert tableview.get_current_row_data() is None

    # Select the rows of table one after the other.
    for row in range(len(TABLE_DATAF)):
        index = tableview.proxy_model.index(row, 0)
        visual_rect = tableview.visualRect(index)
        qtbot.mouseClick(
            tableview.viewport(), Qt.LeftButton, pos=visual_rect.center())

        assert_frame_equal(tableview.get_current_row_data(),
                           TABLE_DATAF.iloc[[row]])


def test_toggle_column_visibility(tablewidget, qtbot):
    """Test toggling on and off the visibility of the columns."""
    tableview = tablewidget.tableview
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
    menu = tablewidget._column_options_button.menu()
    menu.actions()[1].trigger()
    for action in tableview._toggle_column_visibility_actions:
        assert action.isChecked()
    for logical_index in range(tableview.column_count()):
        assert not horiz_header.isSectionHidden(logical_index)
    assert tableview.visible_column_count() == NCOL
    assert tableview.hidden_column_count() == 0


def test_restore_columns_to_defaults(tablewidget, qtbot):
    """Test restoring the visibility and order of the columns."""
    tableview = tablewidget.tableview
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
    menu = tablewidget._column_options_button.menu()
    menu.actions()[0].trigger()
    assert horiz_header.logicalIndex(0) == 0
    assert horiz_header.logicalIndex(2) == 2
    assert action.isChecked()
    assert not horiz_header.isSectionHidden(logical_index)
    assert tableview.visible_column_count() == NCOL
    assert tableview.hidden_column_count() == 0


def test_edit_non_editable_cell(tablewidget, qtbot):
    """
    Test editing the content of a non editable cell.
    """
    tableview = tablewidget.tableview

    # Select a table cell whose content is not editable and try to edit it.
    model_index = tableview.model().index(0, 4)
    qtbot.mouseClick(
        tableview.viewport(),
        Qt.LeftButton,
        pos=tableview.visualRect(model_index).center())

    item_delegate = tableview.itemDelegate(model_index)
    assert model_index.data() == 'not editable'
    assert isinstance(item_delegate, NotEditableDelegate)

    # Try to edit the content of the selected cell.
    qtbot.keyPress(tableview, Qt.Key_Enter)
    assert tableview.state() != tableview.EditingState

    # Try to clear the content of the selected cell.
    assert item_delegate.is_required
    assert model_index.data() == 'not editable'
    assert tableview.model().get_value_at(model_index) == 'not editable'
    qtbot.keyPress(tableview, Qt.Key_Delete, modifier=Qt.ControlModifier)
    assert model_index.data() == 'not editable'
    assert tableview.model().get_value_at(model_index) == 'not editable'


def test_edit_editable_cell(tablewidget, qtbot):
    """
    Test editing the content of an editable cell.
    """
    tableview = tablewidget.tableview

    expected_data = ['str1', 'Yes', '1.111', '3']
    expected_value = ['str1', True, 1.111, 3]
    expected_edited_data = ['new_str1', 'No', '1.234', '7']
    expected_edited_value = ['new_str1', False, 1.234, 7]

    for i in range(4):
        # Select the editable table cell at model index(0, i).
        qtbot.mouseClick(
            tableview.viewport(),
            Qt.LeftButton,
            pos=tableview.visualRect(tableview.model().index(0, i)).center())

        model_index = tableview.selectionModel().currentIndex()
        item_delegate = tableview.itemDelegate(model_index)
        assert model_index.data() == expected_data[i]

        # Edit the value of the cell and cancel the edit.
        qtbot.keyPress(tableview, Qt.Key_Enter)

        assert tableview.state() == tableview.EditingState
        qtbot.keyClicks(item_delegate.editor, expected_edited_data[i])
        qtbot.keyPress(item_delegate.editor, Qt.Key_Escape)
        assert tableview.state() != tableview.EditingState

        assert model_index.data() == expected_data[i]
        assert tableview.model().get_value_at(model_index) == expected_value[i]
        assert len(tableview.source_model._dataf_edits) == i

        # Edit the value of the cell and accept the edit.
        qtbot.keyPress(tableview, Qt.Key_Enter)

        assert tableview.state() == tableview.EditingState
        qtbot.keyClicks(item_delegate.editor, expected_edited_data[i])
        qtbot.keyPress(item_delegate.editor, Qt.Key_Enter)
        assert tableview.state() != tableview.EditingState

        assert model_index.data() == expected_edited_data[i]
        assert (tableview.model().get_value_at(model_index) ==
                expected_edited_value[i])
        assert len(tableview.source_model._dataf_edits) == i + 1


def test_clearing_required_cell(tablewidget, qtbot):
    """
    Test clearing the content of cell that required a non null value.
    """
    tableview = tablewidget.tableview
    model_index = tableview.model().index(0, 0)
    assert tableview.itemDelegate(model_index).is_required
    assert model_index.data() == 'str1'
    assert tableview.model().get_value_at(model_index) == 'str1'

    # Select a table cell that requires a non null value.
    qtbot.mouseClick(
        tableview.viewport(),
        Qt.LeftButton,
        pos=tableview.visualRect(model_index).center())

    # Try to clear the content of the selected cell.
    qtbot.keyPress(tableview, Qt.Key_Delete, modifier=Qt.ControlModifier)
    assert model_index.data() == 'str1'
    assert tableview.model().get_value_at(model_index) == 'str1'


def test_clearing_non_required_cell(tablewidget, qtbot):
    """
    Test clearing the content of cell that required a non null value.
    """
    tableview = tablewidget.tableview
    model_index = tableview.model().index(0, 2)
    assert not tableview.itemDelegate(model_index).is_required
    assert model_index.data() == '1.111'
    assert tableview.model().get_value_at(model_index) == 1.111

    # Select a table cell that does not require a non null value.
    qtbot.mouseClick(
        tableview.viewport(),
        Qt.LeftButton,
        pos=tableview.visualRect(model_index).center())

    # Try to clear the content of the selected cell.
    qtbot.keyPress(tableview, Qt.Key_Delete, modifier=Qt.ControlModifier)
    assert model_index.data() == ''
    assert tableview.model().get_value_at(model_index) is None


def test_cancel_edits(tablewidget, qtbot):
    """
    Test cancelling all edits made to the table's data.
    """
    tableview = tablewidget.tableview

    # Do some edits to the table's data programmatically.
    expected_data = ['new_str1', 'No', '1.234', '7']
    expected_value = ['new_str1', False, 1.234, 7]

    assert tableview.model().has_unsaved_data_edits() is False
    for i in range(4):
        model_index = tableview.model().index(0, i)
        tableview.model().set_data_edits_at(model_index, expected_value[i])
        assert model_index.data() == expected_data[i]
        assert tableview.model().get_value_at(model_index) == expected_value[i]
    assert len(tableview.source_model._dataf_edits) == i + 1
    assert tableview.model().has_unsaved_data_edits() is True

    # Cancel all edits.
    expected_data = ['str1', 'Yes', '1.111', '3']
    expected_value = ['str1', True, 1.111, 3]

    tableview.model().cancel_all_data_edits()
    for i in range(4):
        model_index = tableview.model().index(0, i)
        assert model_index.data() == expected_data[i]
        assert tableview.model().get_value_at(model_index) == expected_value[i]
    assert tableview.model().has_unsaved_data_edits() is False
    assert len(tableview.source_model._dataf_edits) == 0


def test_undo_edits(tablewidget, qtbot):
    """
    Test undo edit action in table view.
    """
    tableview = tablewidget.tableview

    # Do some edits to the table's data programmatically in the first row
    # of the table.
    expected_data = ['new_str1', 'No', '1.234', '7']
    expected_value = ['new_str1', False, 1.234, 7]
    for i in range(4):
        model_index = tableview.model().index(0, i)
        tableview.model().set_data_edits_at(model_index, expected_value[i])
        assert model_index.data() == expected_data[i]
        assert tableview.model().get_value_at(model_index) == expected_value[i]

    # Undo the edits one by one with keyboard shortcut Ctrl+Z.
    original_data = ['str1', 'Yes', '1.111', '3', 'not editable']
    original_value = ['str1', True, 1.111, 3, 'not editable']
    for i in reversed(range(4)):
        qtbot.keyPress(tablewidget, Qt.Key_Z, modifier=Qt.ControlModifier)
        model_index = tableview.model().index(0, i)
        assert model_index.data() == original_data[i]
        assert tableview.model().get_value_at(model_index) == original_value[i]


def test_save_edits(tablewidget, qtbot):
    """
    Test saving all edits made to the table's data.
    """
    tableview = tablewidget.tableview

    expected_data = ['new_str1', 'No', '1.234', '7']
    expected_value = ['new_str1', False, 1.234, 7]

    # Do some edits to the table's data programmatically.
    assert len(tableview.source_model._dataf_edits) == 0
    assert tableview.model().has_unsaved_data_edits() is False
    for i in range(4):
        model_index = tableview.model().index(0, i)
        tableview.model().set_data_edits_at(model_index, expected_value[i])
        assert model_index.data() == expected_data[i]
        assert tableview.model().get_value_at(model_index) == expected_value[i]
    assert len(tableview.source_model._dataf_edits) == i + 1
    assert tableview.model().has_unsaved_data_edits() is True

    # Save all edits.
    tableview.model().save_data_edits()
    qtbot.wait(100)

    assert len(tableview.source_model._dataf_edits) == 0
    assert tableview.model().has_unsaved_data_edits() is False
    for i in range(4):
        model_index = tableview.model().index(0, i)
        assert model_index.data() == expected_data[i]
        assert tableview.model().get_value_at(model_index) == expected_value[i]


def test_select_all_and_clear(tablewidget, qtbot, TABLE_DATAF):
    """
    Test select all and clear actions.
    """
    tableview = tablewidget.tableview
    selection_model = tablewidget.tableview.selectionModel()

    # Set a current index of the model selection.
    expected_model_index = tableview.model().index(1, 1)
    selection_model.setCurrentIndex(
        expected_model_index, selection_model.Current)
    assert selection_model.currentIndex() == expected_model_index
    assert len(selection_model.selectedIndexes()) == 0

    # Select all cells with keyboard shortcut Ctrl+A.
    qtbot.keyPress(tablewidget, Qt.Key_A, modifier=Qt.ControlModifier)
    assert selection_model.currentIndex() == expected_model_index
    assert len(selection_model.selectedIndexes()) == NCOL * len(TABLE_DATAF)

    # Clear all cells with keyboard shortcut Escape.
    qtbot.keyPress(tablewidget, Qt.Key_Escape)
    assert selection_model.currentIndex() == expected_model_index
    assert len(selection_model.selectedIndexes()) == 0


def test_select_row(tablewidget, qtbot):
    """
    Test select row action.
    """
    model = tablewidget.tableview.model()
    selection_model = tablewidget.tableview.selectionModel()

    # Set a current index of the model selection.
    expected_index = model.index(1, 1)
    selection_model.setCurrentIndex(expected_index, selection_model.Current)
    assert selection_model.currentIndex() == expected_index
    assert len(selection_model.selectedIndexes()) == 0

    # Select some cells in the table, one in the first row and another one
    # in the third row.
    selection_model.select(model.index(0, 1), selection_model.Select)
    selection_model.select(model.index(2, 0), selection_model.Select)
    assert selection_model.currentIndex() == expected_index
    assert len(selection_model.selectedIndexes()) == 2

    # Select rows with keyboard shortcut Shift+Space.
    qtbot.keyPress(tablewidget, Qt.Key_Space, modifier=Qt.ShiftModifier)
    assert selection_model.currentIndex() == expected_index
    assert len(selection_model.selectedIndexes()) == NCOL * 2
    assert [index.row() for index in selection_model.selectedRows()] == [0, 2]


def test_select_column(tablewidget, qtbot, TABLE_DATAF):
    """
    Test select column action.
    """
    model = tablewidget.tableview.model()
    selection_model = tablewidget.tableview.selectionModel()

    # Set a current index of the model selection.
    expected_index = model.index(1, 1)
    selection_model.setCurrentIndex(expected_index, selection_model.Current)
    assert selection_model.currentIndex() == expected_index
    assert len(selection_model.selectedIndexes()) == 0

    # Select some cells in the table, one in the second column and another one
    # in the fourth column.
    selection_model.select(model.index(0, 1), selection_model.Select)
    selection_model.select(model.index(2, 3), selection_model.Select)
    assert selection_model.currentIndex() == expected_index
    assert len(selection_model.selectedIndexes()) == 2

    # Select columns with keyboard shortcut Ctrl+Space.
    qtbot.keyPress(tablewidget, Qt.Key_Space, modifier=Qt.ControlModifier)
    assert selection_model.currentIndex() == expected_index
    assert len(selection_model.selectedIndexes()) == len(TABLE_DATAF) * 2
    assert tablewidget.tableview.get_selected_columns() == [1, 3]


def test_move_current_to_border(tablewidget, qtbot, TABLE_DATAF):
    """
    Test the shortcuts to move the current cell to the border of the table with
    the Ctrl + Arrow key shortcuts.
    """
    model = tablewidget.tableview.model()
    selection_model = tablewidget.tableview.selectionModel()

    # Set a current index of the model selection.
    expected_index = model.index(0, 2)
    selection_model.setCurrentIndex(expected_index, selection_model.Select)
    assert selection_model.currentIndex() == expected_index
    assert selection_model.selectedIndexes() == [expected_index]

    # Move current index to the end of the row with Ctrl+Right
    expected_index = model.index(0, NCOL - 1)
    qtbot.keyPress(tablewidget, Qt.Key_Right, modifier=Qt.ControlModifier)
    assert selection_model.currentIndex() == expected_index
    assert selection_model.selectedIndexes() == [expected_index]

    # Move current index to the bottom of the column with Ctrl+Down
    expected_index = model.index(len(TABLE_DATAF) - 1, NCOL - 1)
    qtbot.keyPress(tablewidget, Qt.Key_Down, modifier=Qt.ControlModifier)
    assert selection_model.currentIndex() == expected_index
    assert selection_model.selectedIndexes() == [expected_index]

    # Move current index to the start of the row with Ctrl+Left
    expected_index = model.index(len(TABLE_DATAF) - 1, 0)
    qtbot.keyPress(tablewidget, Qt.Key_Left, modifier=Qt.ControlModifier)
    assert selection_model.currentIndex() == expected_index
    assert selection_model.selectedIndexes() == [expected_index]

    # Move current index to the top of the column with Ctrl+Up
    expected_index = model.index(0, 0)
    qtbot.keyPress(tablewidget, Qt.Key_Up, modifier=Qt.ControlModifier)
    assert selection_model.currentIndex() == expected_index
    assert selection_model.selectedIndexes() == [expected_index]


def test_extend_selection_to_border(tablewidget, qtbot):
    """
    Test the shortcuts to select all cell between the current selection and
    one of the table's border is working correctly with the
    Ctrl + Shift + Arrow key shortcuts.
    """
    model = tablewidget.tableview.model()
    selection_model = tablewidget.tableview.selectionModel()

    # Set a current index and select some cells in the table.
    expected_current_index = model.index(1, 1)
    selection_model.setCurrentIndex(
        expected_current_index, selection_model.Current)
    selection_model.select(model.index(1, 2), selection_model.Select)
    selection_model.select(model.index(1, 4), selection_model.Select)

    assert selection_model.currentIndex() == expected_current_index
    assert len(selection_model.selectedIndexes()) == 2

    # Select all cells above selection with Ctrl+Shift+Up.
    qtbot.keyPress(tablewidget, Qt.Key_Up,
                   modifier=Qt.ControlModifier | Qt.ShiftModifier)

    selected_indexes = selection_model.selectedIndexes()
    expected_selected_indexes = [(0, 1), (0, 2), (1, 1), (1, 2), (1, 4)]
    assert selection_model.currentIndex() == expected_current_index
    assert len(selected_indexes) == len(expected_selected_indexes)
    for index in expected_selected_indexes:
        assert model.index(*index) in selected_indexes

    # Select all cells to the left of selection with Ctrl+Shift+Left.
    qtbot.keyPress(tablewidget, Qt.Key_Left,
                   modifier=Qt.ControlModifier | Qt.ShiftModifier)

    selected_indexes = selection_model.selectedIndexes()
    expected_selected_indexes = [
        (0, 0), (1, 0), (0, 1), (0, 2), (1, 1), (1, 2), (1, 4)]
    assert selection_model.currentIndex() == expected_current_index
    assert len(selected_indexes) == len(expected_selected_indexes)
    for index in expected_selected_indexes:
        assert model.index(*index) in selected_indexes


def test_horiz_header_single_mouse_click(tablewidget, qtbot):
    """
    Test that single mouse clicking on a header section select the
    corresponding column and do NOT sort the data.
    """
    tableview = tablewidget.tableview
    horiz_header = tablewidget.tableview.horizontalHeader()
    model = tableview.model()

    # Single mouse click on the first section of the horizontal header
    # and assert that the column was selected and that NO sorting was done.
    visual_rect = horiz_header.visual_rect_at(0)
    qtbot.mouseClick(
        horiz_header.viewport(), Qt.LeftButton, pos=visual_rect.center())

    assert tableview.get_selected_columns() == [0]
    assert get_values_for_column(model.index(0, 0)) == ['str1', 'str2', 'str3']
    assert horiz_header.sortIndicatorOrder() == 0
    assert horiz_header.sortIndicatorSection() == -1


def test_horiz_header_double_mouse_click(tablewidget, qtbot):
    """
    Test that double mouse clicking on a header section sort the data
    according to that column (instead of single clicking).
    """
    tableview = tablewidget.tableview
    horiz_header = tablewidget.tableview.horizontalHeader()
    model = tableview.model()

    clicked_column_index = 3
    visual_rect = horiz_header.visual_rect_at(clicked_column_index)

    # We need first to single mouse click to select the column.
    qtbot.mouseClick(
        horiz_header.viewport(), Qt.LeftButton, pos=visual_rect.center())
    assert tableview.get_selected_columns() == [clicked_column_index]

    # Double mouse click on the fourth section and assert that the
    # data were sorted in ASCENDING order according to that column.
    qtbot. mouseDClick(
        horiz_header.viewport(), Qt.LeftButton, pos=visual_rect.center())

    assert tableview.get_selected_columns() == [clicked_column_index]
    assert get_values_for_column(model.index(0, 0)) == ['str2', 'str3', 'str1']
    assert horiz_header.sortIndicatorOrder() == 0
    assert horiz_header.sortIndicatorSection() == clicked_column_index

    # Double mouse click again on the fourth section and assert that the
    # data were sorted in DESCENDING order according to that column.
    qtbot. mouseDClick(
        horiz_header.viewport(), Qt.LeftButton, pos=visual_rect.center())

    assert tableview.get_selected_columns() == [clicked_column_index]
    assert get_values_for_column(model.index(0, 0)) == ['str1', 'str3', 'str2']
    assert horiz_header.sortIndicatorOrder() == 1
    assert horiz_header.sortIndicatorSection() == clicked_column_index


def test_column_sorting(tablewidget, qtbot):
    """
    Test that sorting by column work as expected.
    """
    tableview = tablewidget.tableview
    selection_model = tablewidget.tableview.selectionModel()
    horiz_header = tablewidget.tableview.horizontalHeader()
    model = tableview.model()

    # Select a cell in column 4 of the table.
    selected_column_index = 3
    selected_model_index = model.index(1, selected_column_index)
    selection_model.setCurrentIndex(
        selected_model_index, selection_model.SelectCurrent)
    assert selection_model.currentIndex() == selected_model_index
    assert len(selection_model.selectedIndexes()) == 1

    # Sort in ascending order according to the current column using the
    # keyboard shorcut Ctrl+<.
    qtbot.keyPress(tableview, Qt.Key_Less, modifier=Qt.ControlModifier)
    assert get_values_for_column(model.index(0, 0)) == ['str2', 'str3', 'str1']
    assert horiz_header.sortIndicatorOrder() == 0
    assert horiz_header.sortIndicatorSection() == selected_column_index

    # Sort in descending order according to the current column using the
    # keyboard shorcut Ctrl+>.
    qtbot.keyPress(tableview, Qt.Key_Greater, modifier=Qt.ControlModifier)
    assert get_values_for_column(model.index(0, 0)) == ['str1', 'str3', 'str2']
    assert horiz_header.sortIndicatorOrder() == 1
    assert horiz_header.sortIndicatorSection() == selected_column_index

    # Clear sorting.
    qtbot.keyPress(tableview, Qt.Key_Period, modifier=Qt.ControlModifier)
    tableview._actions['sort'][-1].trigger()
    assert get_values_for_column(model.index(0, 0)) == ['str1', 'str2', 'str3']
    assert horiz_header.sortIndicatorOrder() == 0
    assert horiz_header.sortIndicatorSection() == -1


def test_copy_to_clipboard(tablewidget, qtbot, mocker):
    """
    Test that the function to copy the content of the selected cells to the
    clipboard is working as expected.
    """
    tableview = tablewidget.tableview
    selection_model = tablewidget.tableview.selectionModel()
    model = tablewidget.tableview.model()
    mocker.patch.object(QMessageBox, 'information')
    QApplication.clipboard().clear()

    # Try to copy something to the clipboard when nothing is selected
    # in the table.
    qtbot.keyPress(tableview, Qt.Key_C, modifier=Qt.ControlModifier)
    assert QApplication.clipboard().text() == ''

    # Do an invalid selection in the table and copy the selection to the
    # clipboard using the keyboard shorcut Ctrl+S.
    coord_to_select = [(0, 0), (0, 1), (2, 0), (2, 2)]
    for coord in coord_to_select:
        selection_model.select(model.index(*coord), selection_model.Select)
    qtbot.keyPress(tableview, Qt.Key_C, modifier=Qt.ControlModifier)

    assert QApplication.clipboard().text() == ''

    # Clear the selection of the table.
    qtbot.keyPress(tableview, Qt.Key_Escape)

    # Do a valid selection in the table and copy the selection to the
    # clipboard using the keyboard shorcut Ctrl+S.
    coord_to_select = [(0, 0), (0, 2), (2, 0), (2, 2)]
    for coord in coord_to_select:
        selection_model.select(model.index(*coord), selection_model.Select)
    qtbot.keyPress(tableview, Qt.Key_C, modifier=Qt.ControlModifier)

    assert QApplication.clipboard().text() == 'str1\t1.111\nstr3\t3.333'


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw', '-s'])