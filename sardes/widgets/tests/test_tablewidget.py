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
import os.path as osp
import uuid

# ---- Third party imports
import numpy as np
import pytest
import pandas as pd
from pandas.testing import assert_frame_equal
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication

# ---- Local imports
from sardes.api.tablemodels import SardesTableModel
from sardes.config.locale import _
from sardes.widgets.tableviews import (
    SardesTableWidget, NotEditableDelegate, StringEditDelegate,
    NumEditDelegate, BoolEditDelegate, MSEC_MIN_PROGRESS_DISPLAY,
    QMessageBox, QCheckBox)
from sardes.database.database_manager import DatabaseConnectionManager
from sardes.api.database_accessor import DatabaseAccessor


# =============================================================================
# ---- Fixtures
# =============================================================================
NCOL = 6
COLUMNS = ['col{}'.format(i) for i in range(NCOL)]
HEADERS = [_('Column #{}').format(i) for i in range(NCOL)]
VALUES = [['str1', True, 1.111, 3, 'not editable', None],
          ['str2', False, 2.222, 1, 'not editable', None],
          ['str3', True, 3.333, 29, 'not editable', None]]
INDEXES = [uuid.uuid4() for i in range(len(VALUES))]

@pytest.fixture
def TABLE_DATAF():
    dataf = pd.DataFrame(
        np.array(VALUES),
        index=INDEXES,
        columns=COLUMNS
        )
    dataf['col3'] = dataf['col3'].astype(pd.Int64Dtype())
    return dataf


@pytest.fixture
def tablemodel(qtbot, TABLE_DATAF):

    class DatabaseAccessorTest(DatabaseAccessor):
        def is_connected(self):
            return self._connection is not None

        def _connect(self):
            self._connection = True

        def close_connection(self):
            self._connection = None

        def _create_index(self, name):
            return uuid.uuid4()

        def get_test_table_dataf_name(self, *args, **kargs):
            return TABLE_DATAF.copy()

        def set_test_table_dataf_name(self, index, column, edited_value):
            TABLE_DATAF.loc[index, column] = edited_value

        def delete_test_table_dataf_name(self, index):
            TABLE_DATAF.drop(index, axis='index', inplace=True)

        def add_test_table_dataf_name(self, index, attribute_values):
            for column in TABLE_DATAF.columns:
                TABLE_DATAF.loc[index, column] = (
                    attribute_values.get(column, None))

    class SardesTableModelMock(SardesTableModel):
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

    # Setup table and database connection manager.
    tablemodel = SardesTableModelMock(
        table_title='Sardes Test Table',
        table_id='sardes_test_table',
        data_columns_mapper=[
            (col, header) for col, header in zip(COLUMNS, HEADERS)]
        )

    db_connection_manager = DatabaseConnectionManager()
    db_connection_manager.register_model(tablemodel, 'test_table_dataf_name')
    db_connection_manager.connect_to_db(DatabaseAccessorTest())

    # We need to connect manually the database manager data changed signal
    # to the method to update data because this is handled on the plugin side.
    db_connection_manager.sig_database_data_changed.connect(
        tablemodel.update_data)

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
    # qtbot.addWidget(tablewidget)

    # Assert everything is working as expected when table is empty.
    assert tablewidget
    assert tablewidget.tableview.model().rowCount() == 0
    assert tablewidget.tableview.model().columnCount() == NCOL
    assert tablewidget.tableview.visible_row_count() == 0

    # Fetch the model data explicitely. We need to do this because
    # the table view that we use for testing is not connected to a
    # database connection manager.
    tablewidget.update_model_data()
    qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)

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


def get_selected_data(tablewidget):
    return ([index.data() for index in
             tablewidget.tableview.selectionModel().selectedIndexes()])


# =============================================================================
# ---- Tests
# =============================================================================
def test_tablewidget_init(tablewidget, TABLE_DATAF):
    """Test that SardesTableWidget is initialized correctly."""
    tableview = tablewidget.tableview
    horiz_header = tablewidget.tableview.horizontalHeader()
    model = tableview.model()

    # Assert that the content of the table is as expected.
    assert_frame_equal(tableview.model().dataf, TABLE_DATAF)
    assert tableview.visible_row_count() == len(TABLE_DATAF)
    assert (tablewidget.selected_line_count.text() ==
            "{} out of {} row(s) selected ".format(0, len(TABLE_DATAF)))

    # Assert that all columns are visible.
    for action in tableview.get_column_visibility_actions():
        assert action.isChecked()
    for logical_index in range(tableview.column_count()):
        assert not tableview.horizontalHeader().isSectionHidden(logical_index)

    # Assert that no column is initially selected.
    assert tableview.get_selected_columns() == []

    # Assert that the data are not initially sorted.
    assert get_values_for_column(model.index(0, 0)) == ['str1', 'str2', 'str3']
    assert horiz_header.sort_indicator_order() == []
    assert horiz_header.sort_indicator_sections() == []

    # Assert there is no edits made to the data.
    assert not tableview.model().has_unsaved_data_edits()
    assert tableview.model().data_edit_count() == 0


def test_clear_data(tablewidget):
    """Test that clearing data is working as expected."""
    tablewidget.clear_model_data()
    assert tablewidget.tableview.row_count() == 0


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


def test_get_current_row_data(tablewidget, qtbot, TABLE_DATAF):
    """
    Test the data returned for the row with the current index.

    Regression test for cgq-qgc/sardes#117
    """
    tableview = tablewidget.tableview
    assert_frame_equal(tableview.get_current_row_data(), TABLE_DATAF.iloc[[0]])

    # Let's sort the data first since this can cause some problems as
    # pointed out in cgq-qgc/sardes#117
    tableview.sort_by_column(3, Qt.AscendingOrder)
    sorted_dataf = TABLE_DATAF.copy().sort_values(by='col3', ascending=True)

    # Select the rows of table one after the other.
    for row in range(len(sorted_dataf)):
        index = tableview.model().index(row, 0)
        visual_rect = tableview.visualRect(index)
        qtbot.mouseClick(
            tableview.viewport(), Qt.LeftButton, pos=visual_rect.center())

        assert_frame_equal(tableview.get_current_row_data(),
                           sorted_dataf.iloc[[row]])


def test_selected_row_count(tablewidget, qtbot, TABLE_DATAF):
    """
    Test selected row count.
    """
    tablewidget.tableview.selectAll()
    assert tablewidget.tableview.selected_row_count() == len(TABLE_DATAF)


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
    assert not tableview.edit_item_action.isEnabled()
    assert not tableview.clear_item_action.isEnabled()

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
        assert tableview.edit_item_action.isEnabled()

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
        assert tableview.model().data_edit_count() == i

        # Edit the value of the cell and accept the edit.
        qtbot.keyPress(tableview, Qt.Key_Enter)

        assert tableview.state() == tableview.EditingState
        qtbot.keyClicks(item_delegate.editor, expected_edited_data[i])
        qtbot.keyPress(item_delegate.editor, Qt.Key_Enter)
        assert tableview.state() != tableview.EditingState

        assert model_index.data() == expected_edited_data[i]
        assert (tableview.model().get_value_at(model_index) ==
                expected_edited_value[i])
        assert tableview.model().data_edit_count() == i + 1


def test_edit_integer(tablewidget, qtbot, mocker):
    """
    Test editing the content of an cell containing an integer.

    Regression test for cgq-qgc/sardes#231
    """
    tableview = tablewidget.tableview
    model_index = tableview.model().index(2, 3)

    # Select cell at model_index.
    qtbot.mouseClick(
        tableview.viewport(),
        Qt.LeftButton,
        pos=tableview.visualRect(model_index).center())
    assert model_index.data() == '29'
    assert tableview.model().get_value_at(model_index) == 29

    # Clear the value in the current cell.
    qtbot.keyPress(tableview, Qt.Key_Delete)
    assert model_index.data() == ''
    assert pd.isnull(tableview.model().get_value_at(model_index))

    # Save edits.
    patcher = mocker.patch.object(
        QMessageBox, 'exec_', return_value=QMessageBox.Cancel)
    qtbot.keyPress(tablewidget, Qt.Key_Enter, modifier=Qt.ControlModifier)
    qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)

    # Select back cell at model_index.
    qtbot.mouseClick(
        tableview.viewport(),
        Qt.LeftButton,
        pos=tableview.visualRect(model_index).center())
    assert model_index.data() == ''
    assert pd.isnull(tableview.model().get_value_at(model_index))

    # Edit the value in the current cell.
    item_delegate = tableview.itemDelegate(model_index)
    qtbot.keyPress(tableview, Qt.Key_Enter)
    item_delegate.editor.setValue(24)
    qtbot.keyPress(item_delegate.editor, Qt.Key_Enter)
    assert model_index.data() == '24'
    assert tableview.model().get_value_at(model_index) == 24


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
    assert not tableview.clear_item_action.isEnabled()

    # Try to clear the content of the selected cell.
    qtbot.keyPress(tableview, Qt.Key_Delete, modifier=Qt.ControlModifier)
    assert model_index.data() == 'str1'
    assert tableview.model().get_value_at(model_index) == 'str1'
    assert not tableview.clear_item_action.isEnabled()


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
    assert tableview.clear_item_action.isEnabled()

    # Try to clear the content of the selected cell.
    qtbot.keyPress(tableview, Qt.Key_Delete)
    assert model_index.data() == ''
    assert tableview.model().get_value_at(model_index) is None
    assert not tableview.clear_item_action.isEnabled()


def test_add_row(tablewidget, qtbot, mocker, TABLE_DATAF):
    """
    Test that adding a new row to the table is working as expected.
    """
    tableview = tablewidget.tableview
    selection_model = tablewidget.tableview.selectionModel()
    assert len(TABLE_DATAF) == 3

    # Add 3 new rows.
    nrow = len(TABLE_DATAF)
    for i in range(3):
        qtbot.keyPress(tableview, Qt.Key_Plus, modifier=Qt.ControlModifier)
        nrow += 1
    assert tableview.row_count() == 6
    assert len(TABLE_DATAF) == 3
    assert selection_model.currentIndex() == tableview.model().index(5, 0)

    # Undo the last row added.
    qtbot.keyPress(tablewidget, Qt.Key_Z, modifier=Qt.ControlModifier)
    nrow += -1
    assert tableview.row_count() == 5
    assert len(TABLE_DATAF) == 3
    assert selection_model.currentIndex() == tableview.model().index(4, 0)

    # Save the results.
    mocker.patch.object(QMessageBox, 'exec_', return_value=QMessageBox.Save)
    qtbot.keyPress(tablewidget, Qt.Key_Enter, modifier=Qt.ControlModifier)
    qtbot.wait(100)
    assert tableview.row_count() == 5
    assert len(TABLE_DATAF) == 5


def test_delete_row(tablewidget, qtbot, mocker, TABLE_DATAF):
    """
    Test that deleting a row in the table is working as expected.
    """
    tableview = tablewidget.tableview
    selection_model = tablewidget.tableview.selectionModel()
    model = tableview.model()
    assert len(TABLE_DATAF) == 3
    assert tableview.row_count() == 3

    # Delete the selected rows.
    selection_model.setCurrentIndex(
        model.index(0, 0), selection_model.SelectCurrent)
    selection_model.select(model.index(2, 1), selection_model.Select)
    assert tableview.get_rows_intersecting_selection() == [0, 2]

    qtbot.keyPress(tableview, Qt.Key_Minus, modifier=Qt.ControlModifier)
    assert len(TABLE_DATAF) == 3
    assert tableview.row_count() == 3
    assert tableview.model().data_edit_count() == 1
    assert tableview.model().has_unsaved_data_edits() is True

    # Undo the last row delete operation.
    qtbot.keyPress(tablewidget, Qt.Key_Z, modifier=Qt.ControlModifier)
    assert len(TABLE_DATAF) == 3
    assert tableview.row_count() == 3
    assert tableview.model().data_edit_count() == 0
    assert tableview.model().has_unsaved_data_edits() is False

    # Delete back the row where the table cursor is.
    selection_model.setCurrentIndex(
        model.index(0, 0), selection_model.SelectCurrent)
    selection_model.select(model.index(2, 1), selection_model.Select)
    assert tableview.get_rows_intersecting_selection() == [0, 2]

    qtbot.keyPress(tableview, Qt.Key_Minus, modifier=Qt.ControlModifier)
    assert len(TABLE_DATAF) == 3
    assert tableview.row_count() == 3
    assert tableview.model().data_edit_count() == 1
    assert tableview.model().has_unsaved_data_edits() is True

    # Save the results.
    mocker.patch.object(QMessageBox, 'exec_', return_value=QMessageBox.Save)
    qtbot.keyPress(tablewidget, Qt.Key_Enter, modifier=Qt.ControlModifier)
    qtbot.wait(100)
    assert len(TABLE_DATAF) == 1
    assert tableview.row_count() == 1


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
        tableview.model().set_data_edit_at(model_index, expected_value[i])
        assert model_index.data() == expected_data[i]
        assert tableview.model().get_value_at(model_index) == expected_value[i]
    assert tableview.model().data_edit_count() == i + 1
    assert tableview.model().has_unsaved_data_edits() is True

    # Cancel all edits.
    expected_data = ['str1', 'Yes', '1.111', '3']
    expected_value = ['str1', True, 1.111, 3]

    tableview.model().cancel_data_edits()
    for i in range(4):
        model_index = tableview.model().index(0, i)
        assert model_index.data() == expected_data[i]
        assert tableview.model().get_value_at(model_index) == expected_value[i]
    assert tableview.model().has_unsaved_data_edits() is False
    assert tableview.model().data_edit_count() == 0


def test_undo_when_not_unsaved_data_edits(tablewidget, qtbot):
    """
    Test undo edit action in table view.

    Regression test for cgq-qgc/sardes#118
    """
    model = tablewidget.tableview.model()

    # Do 3 successive edits on a cell, where the second edit bring back the
    # value of the cell to that of the original value.
    model_index = model.index(0, 0)
    model.set_data_edit_at(model_index, 'new_str1')
    model.set_data_edit_at(model_index, 'str1')
    model.set_data_edit_at(model_index, 'new_new_str1')

    assert model.data_edit_count() == 3
    assert model_index.data() == 'new_new_str1'
    assert model.get_value_at(model_index) == 'new_new_str1'
    assert model.has_unsaved_data_edits() is True
    assert model.is_data_edited_at(model_index) is True

    # Undo the 3 edits one after the other.
    qtbot.keyPress(tablewidget, Qt.Key_Z, modifier=Qt.ControlModifier)
    assert model.data_edit_count() == 2
    assert model_index.data() == 'str1'
    assert model.get_value_at(model_index) == 'str1'
    assert model.has_unsaved_data_edits() is False
    assert model.is_data_edited_at(model_index) is False

    qtbot.keyPress(tablewidget, Qt.Key_Z, modifier=Qt.ControlModifier)
    assert model.data_edit_count() == 1
    assert model_index.data() == 'new_str1'
    assert model.get_value_at(model_index) == 'new_str1'
    assert model.has_unsaved_data_edits() is True
    assert model.is_data_edited_at(model_index) is True

    qtbot.keyPress(tablewidget, Qt.Key_Z, modifier=Qt.ControlModifier)
    assert model.data_edit_count() == 0
    assert model_index.data() == 'str1'
    assert model.get_value_at(model_index) == 'str1'
    assert model.has_unsaved_data_edits() is False
    assert model.is_data_edited_at(model_index) is False


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
        tableview.model().set_data_edit_at(model_index, expected_value[i])
        assert model_index.data() == expected_data[i]
        assert tableview.model().get_value_at(model_index) == expected_value[i]
        assert tableview.model().data_edit_count()

    # Undo all remaining edits one by one with keyboard shortcut Ctrl+Z.
    original_data = ['str1', 'Yes', '1.111', '3', 'not editable']
    original_value = ['str1', True, 1.111, 3, 'not editable']
    for i in reversed(range(4)):
        qtbot.keyPress(tablewidget, Qt.Key_Z, modifier=Qt.ControlModifier)
        model_index = tableview.model().index(0, i)
        assert model_index.data() == original_data[i]
        assert tableview.model().get_value_at(model_index) == original_value[i]


def test_save_edits(tablewidget, qtbot, mocker):
    """
    Test saving all edits made to the table's data.
    """
    tableview = tablewidget.tableview

    expected_data = ['new_str1', 'No', '1.234', '7']
    expected_value = ['new_str1', False, 1.234, 7]

    # Do some edits to the table's data programmatically.
    assert tableview.model().data_edit_count() == 0
    assert tableview.model().has_unsaved_data_edits() is False
    for i in range(4):
        model_index = tableview.model().index(0, i)
        tableview.model().set_data_edit_at(model_index, expected_value[i])
        assert model_index.data() == expected_data[i]
        assert tableview.model().get_value_at(model_index) == expected_value[i]
    assert tableview.model().data_edit_count() == i + 1
    assert tableview.model().has_unsaved_data_edits() is True

    # Cancel the saving of data edits.
    patcher = mocker.patch.object(
        QMessageBox, 'exec_', return_value=QMessageBox.Cancel)
    qtbot.keyPress(tablewidget, Qt.Key_Enter, modifier=Qt.ControlModifier)
    qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)

    assert patcher.call_count == 1
    assert tableview.model().data_edit_count() == i + 1
    assert tableview.model().has_unsaved_data_edits() is True

    # To simulate the user checking the 'Do not show' checkbox, we patch the
    # Qt checkbox method 'isChecked'.
    mocker.patch.object(QCheckBox, 'isChecked', return_value=True)

    # Save all edits.
    patcher.return_value = QMessageBox.Save
    with qtbot.waitSignal(tableview.model().sig_data_updated, timeout=5000):
        tablewidget.tableview._save_data_edits(force=False)

    assert patcher.call_count == 2
    assert tableview.model().data_edit_count() == 0
    assert tableview.model().has_unsaved_data_edits() is False
    for i in range(4):
        model_index = tableview.model().index(0, i)
        assert model_index.data() == expected_data[i]
        assert tableview.model().get_value_at(model_index) == expected_value[i]

    # Do another edit.
    model_index = tableview.model().index(0, 0)
    tableview.model().set_data_edit_at(model_index, 'new_new_str1')
    assert tableview.model().data_edit_count() == 1
    assert tableview.model().has_unsaved_data_edits() is True

    # Save the edits and assert that the warning dialog was not shown.
    # with qtbot.waitSignal(tableview.model().sig_data_updated, timeout=5000):
    with qtbot.waitSignal(tableview.model().sig_data_updated, timeout=5000):
        tablewidget.tableview._save_data_edits(force=False)

    assert patcher.call_count == 2
    assert model_index.data() == 'new_new_str1'
    assert tableview.model().get_value_at(model_index) == 'new_new_str1'
    assert tableview.model().data_edit_count() == 0
    assert tableview.model().has_unsaved_data_edits() is False


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
    expected_current_index = model.index(0, 1)
    selection_model.setCurrentIndex(
        expected_current_index, selection_model.SelectCurrent)
    assert selection_model.currentIndex() == expected_current_index
    assert len(selection_model.selectedIndexes()) == 1

    # Select another cell in the table on the third row row.
    selection_model.select(model.index(2, 0), selection_model.Select)
    assert selection_model.currentIndex() == expected_current_index
    assert len(selection_model.selectedIndexes()) == 2

    # Select rows with keyboard shortcut Shift+Space.
    qtbot.keyPress(tablewidget, Qt.Key_Space, modifier=Qt.ShiftModifier)
    assert selection_model.currentIndex() == expected_current_index
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
    Test that single mouse clicking on a header section selects the
    corresponding column and does NOT sort the data.
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
    assert horiz_header.sort_indicator_order() == []
    assert horiz_header.sort_indicator_sections() == []


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
    assert get_values_for_column(model.index(0, 0)) == ['str2', 'str1', 'str3']
    assert horiz_header.sort_indicator_order() == [0]
    assert horiz_header.sort_indicator_sections() == [3]

    # Double mouse click again on the fourth section and assert that the
    # data were sorted in DESCENDING order according to that column.
    qtbot. mouseDClick(
        horiz_header.viewport(), Qt.LeftButton, pos=visual_rect.center())

    assert tableview.get_selected_columns() == [clicked_column_index]
    assert get_values_for_column(model.index(0, 0)) == ['str3', 'str1', 'str2']
    assert horiz_header.sort_indicator_order() == [1]
    assert horiz_header.sort_indicator_sections() == [3]


def test_column_sorting(tablewidget, qtbot):
    """
    Test that sorting by column work as expected.
    """
    tableview = tablewidget.tableview
    selection_model = tablewidget.tableview.selectionModel()
    horiz_header = tablewidget.tableview.horizontalHeader()
    model = tableview.model()

    # Select some cells and set the current index.
    selection_model.select(model.index(1, 2), selection_model.Select)
    selection_model.select(model.index(2, 3), selection_model.Select)
    selection_model.select(model.index(1, 3), selection_model.Select)
    selection_model.setCurrentIndex(
        model.index(1, 3), selection_model.SelectCurrent)

    assert selection_model.currentIndex().data() == '1'
    assert get_selected_data(tablewidget) == ['2.222', '29', '1']

    # Sort in ASCENDING order according to the current column using the
    # keyboard shorcut Ctrl+<.

    # ['str2', False, 2.222, 1, 'not editable', None]
    # ['str1', True, 1.111, 3, 'not editable', None]
    # ['str3', True, 3.333, 29, 'not editable', None]

    qtbot.keyPress(tableview, Qt.Key_Less, modifier=Qt.ControlModifier)
    assert get_values_for_column(model.index(0, 0)) == ['str2', 'str1', 'str3']
    assert horiz_header.sort_indicator_order() == [0]
    assert horiz_header.sort_indicator_sections() == [3]
    assert selection_model.currentIndex().data() == '3'
    assert get_selected_data(tablewidget) == ['1.111', '29', '3']

    # Sort in DESCENDING order according to the current column using the
    # keyboard shorcut Ctrl+>.

    # ['str3', True, 3.333, 29, 'not editable', None]
    # ['str1', True, 1.111, 3, 'not editable', None]
    # ['str2', False, 2.222, 1, 'not editable', None]

    qtbot.keyPress(tableview, Qt.Key_Greater, modifier=Qt.ControlModifier)
    assert get_values_for_column(model.index(0, 0)) == ['str3', 'str1', 'str2']
    assert horiz_header.sort_indicator_order() == [1]
    assert horiz_header.sort_indicator_sections() == [3]
    assert selection_model.currentIndex().data() == '3'
    assert get_selected_data(tablewidget) == ['1.111', '1', '3']

    # Clear sorting.
    qtbot.keyPress(tableview, Qt.Key_Period, modifier=Qt.ControlModifier)
    tableview._actions['sort'][-1].trigger()
    assert get_values_for_column(model.index(0, 0)) == ['str1', 'str2', 'str3']
    assert horiz_header.sort_indicator_order() == []
    assert horiz_header.sort_indicator_sections() == []
    assert selection_model.currentIndex().data() == '1'
    assert get_selected_data(tablewidget) == ['2.222', '29', '1']


def test_single_column_sorting(tablewidget, qtbot):
    """
    Test that sorting by column work as expected when multi column sorting
    is not enabled.
    """
    tableview = tablewidget.tableview
    selection_model = tablewidget.tableview.selectionModel()
    horiz_header = tablewidget.tableview.horizontalHeader()
    model = tableview.model()
    model._multi_columns_sort = False

    # Select a cell in the third column.

    # ['str1', True, 1.111, 3, 'not editable', None]
    # ['str2', False, 2.222, 1, 'not editable', None]
    # ['str3', True, 3.333, 29, 'not editable', None]

    selection_model.setCurrentIndex(
        model.index(0, 2), selection_model.SelectCurrent)

    # Sort in DESCENDING order.
    qtbot.keyPress(tableview, Qt.Key_Greater, modifier=Qt.ControlModifier)
    assert get_values_for_column(model.index(0, 0)) == ['str3', 'str2', 'str1']
    assert horiz_header.sort_indicator_order() == [1]
    assert horiz_header.sort_indicator_sections() == [2]
    assert selection_model.currentIndex().data() == '3.333'

    # ['str3', True, 3.333, 29, 'not editable', None]
    # ['str2', False, 2.222, 1, 'not editable', None]
    # ['str1', True, 1.111, 3, 'not editable', None]

    # Select a cell in the second column.
    selection_model.setCurrentIndex(
        model.index(0, 1), selection_model.SelectCurrent)

    # Sort in ACSENDING order
    qtbot.keyPress(tableview, Qt.Key_Less, modifier=Qt.ControlModifier)
    assert get_values_for_column(model.index(0, 0)) == ['str2', 'str1', 'str3']
    assert horiz_header.sort_indicator_order() == [0]
    assert horiz_header.sort_indicator_sections() == [1]
    assert selection_model.currentIndex().data() == 'No'

    # ['str2', False, 2.222, 1, 'not editable', None]
    # ['str1', True, 1.111, 3, 'not editable', None]
    # ['str3', True, 3.333, 29, 'not editable', None]


def test_multi_column_sorting(tablewidget, qtbot):
    """
    Test that sorting by more than one column work as expected.
    """
    tableview = tablewidget.tableview
    selection_model = tablewidget.tableview.selectionModel()
    horiz_header = tablewidget.tableview.horizontalHeader()
    model = tableview.model()

    # ['str1', True, 1.111, 3, 'not editable', None]
    # ['str2', False, 2.222, 1, 'not editable', None]
    # ['str3', True, 3.333, 29, 'not editable', None]

    # Select a cell in the third column.
    selection_model.setCurrentIndex(
        model.index(0, 2), selection_model.SelectCurrent)

    # Sort in DESCENDING order.
    qtbot.keyPress(tableview, Qt.Key_Greater, modifier=Qt.ControlModifier)
    assert get_values_for_column(model.index(0, 0)) == ['str3', 'str2', 'str1']
    assert horiz_header.sort_indicator_order() == [1]
    assert horiz_header.sort_indicator_sections() == [2]
    assert selection_model.currentIndex().data() == '3.333'

    # ['str3', True, 3.333, 29, 'not editable', None]
    # ['str2', False, 2.222, 1, 'not editable', None]
    # ['str1', True, 1.111, 3, 'not editable', None]

    # Select a cell in the second column.
    selection_model.setCurrentIndex(
        model.index(0, 1), selection_model.SelectCurrent)

    # Sort in ACSENDING order
    qtbot.keyPress(tableview, Qt.Key_Less, modifier=Qt.ControlModifier)
    assert get_values_for_column(model.index(0, 0)) == ['str2', 'str3', 'str1']
    assert horiz_header.sort_indicator_order() == [0, 1]
    assert horiz_header.sort_indicator_sections() == [1, 2]
    assert selection_model.currentIndex().data() == 'No'

    # ['str2', False, 2.222, 1, 'not editable', None]
    # ['str3', True, 3.333, 29, 'not editable', None]
    # ['str1', True, 1.111, 3, 'not editable', None]


def test_auto_column_sorting(tablewidget, qtbot):
    """
    Test that sorting by column is done as expected when editing a value
    in a sorted column.
    """
    tableview = tablewidget.tableview
    selection_model = tablewidget.tableview.selectionModel()
    model = tableview.model()

    # Select some cells and set the current index.
    selection_model.select(model.index(1, 2), selection_model.Select)
    selection_model.select(model.index(2, 3), selection_model.Select)
    selection_model.select(model.index(0, 0), selection_model.Select)
    selection_model.setCurrentIndex(
        model.index(0, 0), selection_model.SelectCurrent)

    assert selection_model.currentIndex().data() == 'str1'
    assert get_selected_data(tablewidget) == ['2.222', '29', 'str1']

    # Sort in ASCENDING order according to the current column using the
    # keyboard shorcut Ctrl+<.
    qtbot.keyPress(tableview, Qt.Key_Less, modifier=Qt.ControlModifier)
    assert get_values_for_column(model.index(0, 0)) == ['str1', 'str2', 'str3']

    # Edit the value of the selected index and assert the values were
    # automatically sorted.
    item_delegate = tableview.itemDelegate(selection_model.currentIndex())
    qtbot.keyPress(tableview, Qt.Key_Enter)
    qtbot.keyClicks(item_delegate.editor, 'str4')
    qtbot.keyPress(item_delegate.editor, Qt.Key_Enter)
    assert get_values_for_column(model.index(0, 0)) == ['str2', 'str3', 'str4']
    assert selection_model.currentIndex().data() == 'str4'
    assert get_selected_data(tablewidget) == ['str4']


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
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
