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
import os
import os.path as osp
import uuid
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
from flaky import flaky
import numpy as np
import pytest
import pandas as pd
from pandas.testing import assert_frame_equal
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication

# ---- Local imports
from sardes.api.tablemodels import SardesTableColumn
from sardes.tables.models import StandardSardesTableModel
from sardes.tables.managers import SardesTableModelsManager
from sardes.config.locale import _
from sardes.widgets.tableviews import (
    SardesTableWidget, MSEC_MIN_PROGRESS_DISPLAY, QMessageBox, QCheckBox,
    ImportFromClipboardTool)
from sardes.tables.delegates import (
    NotEditableDelegate, StringEditDelegate,
    IntEditDelegate, NumEditDelegate, BoolEditDelegate)
from sardes.api.database_model import (
    DATABASE_CONCEPTUAL_MODEL, Table, Column)
from sardes.database.database_manager import DatabaseConnectionManager
from sardes.api.database_accessor import DatabaseAccessorBase
from sardes.utils.data_operations import are_values_equal


# =============================================================================
# ---- Fixtures
# =============================================================================
NCOL = 6
COLUMNS = ['col{}'.format(i) for i in range(NCOL)]
HEADERS = ['Column #{}'.format(i) for i in range(NCOL)]
VALUES = [['str1', True, 1.111, 3, 'not editable', None],
          ['str2', False, 2.222, 1, 'not editable', None],
          ['str3', True, 3.333, 29, 'not editable', None]]
DTYPES = ['str', 'boolean', 'float64', 'Int64', 'str', 'str']
INDEXES = [uuid.uuid4() for i in range(len(VALUES))]


# We need to extend the database conceptual model with our test table.
DATABASE_CONCEPTUAL_MODEL.data['test_table_dataf_name'] = Table(
    columns=(
        Column(name=COLUMNS[i],
               dtype=DTYPES[i],
               desc="Description for {}".format(COLUMNS[i])
               ) for i in range(NCOL)
    )
)


@pytest.fixture
def TABLE_DATAF():
    dataf = pd.DataFrame(
        np.array(VALUES),
        index=INDEXES,
        columns=COLUMNS
        )
    dataf['col1'] = dataf['col1'].astype('boolean')
    dataf['col3'] = dataf['col3'].astype('Int64')
    return dataf


@pytest.fixture
def tablemodel(qtbot, TABLE_DATAF):

    class DatabaseAccessorTest(DatabaseAccessorBase):
        def is_connected(self):
            return self._connection is not None

        def _connect(self):
            connection = True
            connection_error = None
            return connection, connection_error

        def close_connection(self):
            self._connection = None

        def commit_transaction(self):
            # This accessor does not support journal logging.
            pass

        def begin_transaction(self, exclusive=True):
            # This accessor does not support journal logging.
            pass

        def _get_test_table_dataf_name(self, *args, **kargs):
            return TABLE_DATAF.copy()

        def _set_test_table_dataf_name(self, index, attribute_values):
            for column, edited_value in attribute_values.items():
                TABLE_DATAF.loc[index, column] = edited_value

        def _del_test_table_dataf_name(self, indexes):
            TABLE_DATAF.drop(indexes, axis='index', inplace=True)

        def _add_test_table_dataf_name(self, values, indexes=None):
            n = len(values)

            if indexes is None:
                indexes = [uuid.uuid4() for i in range(n)]

            for i in range(n):
                for column in TABLE_DATAF.columns:
                    TABLE_DATAF.loc[indexes[i], column] = (
                        values[i].get(column, None))

    class SardesTableModelMock(StandardSardesTableModel):
        __tabletitle__ = 'Sardes Test Table'
        __tablename__ = 'sardes_test_table'
        __tablecolumns__ = [
            SardesTableColumn(
                'col0', 'Column #0', 'str', notnull=True,
                delegate=StringEditDelegate),
            SardesTableColumn(
                'col1', 'Column #1', 'boolean',
                delegate=BoolEditDelegate),
            SardesTableColumn(
                'col2', 'Column #2', 'float64',
                delegate=NumEditDelegate,
                delegate_options={'decimals': 3}),
            SardesTableColumn(
                'col3', 'Column #3', 'Int64',
                delegate=IntEditDelegate),
            SardesTableColumn(
                'col4', 'Column #4', 'str',
                editable=False,
                delegate=NotEditableDelegate),
            SardesTableColumn(
                'col5', 'Column #5', 'str',
                editable=False,
                delegate=NotEditableDelegate),
            ]

        __dataname__ = 'test_table_dataf_name'
        __libnames__ = []

    # Setup table and database connection manager.
    tablemodel = SardesTableModelMock()

    dbconnmanager = DatabaseConnectionManager()

    table_models_manager = SardesTableModelsManager(dbconnmanager)
    table_models_manager.register_table_model(tablemodel)

    # We need to connect manually the database manager data changed signal
    # to the method to update data because this is handled on the plugin side.
    dbconnmanager.sig_database_data_changed.connect(
        tablemodel.update_data)

    with qtbot.waitSignal(dbconnmanager.sig_database_connection_changed):
        dbconnmanager.connect_to_db(DatabaseAccessorTest())

    return tablemodel


@pytest.fixture
def tablewidget(qtbot, tablemodel):
    tablewidget = SardesTableWidget(tablemodel, statusbar=True)

    # Setup the width of the table so that all columns are shown.
    width = 0
    for i in range(tablewidget.tableview.column_count()):
        width += tablewidget.tableview.horizontalHeader().sectionSize(i)
    tablewidget.tableview.setMinimumWidth(width + 25)

    tablewidget.show()
    qtbot.addWidget(tablewidget)
    qtbot.waitExposed(tablewidget)

    # Assert everything is working as expected when table is empty.
    assert tablewidget
    assert tablewidget.tableview.model().rowCount() == 0
    assert tablewidget.tableview.model().columnCount() == NCOL
    assert tablewidget.tableview.visible_row_count() == 0

    # Fetch the model data explicitely. We need to do this because
    # the table view that we use for testing is not connected to a
    # database connection manager.
    with qtbot.waitSignal(tablewidget.model().sig_data_updated, timeout=5000):
        tablewidget.update_model_data()
    qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY)

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
@flaky(max_runs=3)
def test_tablewidget_init(tablewidget, TABLE_DATAF):
    """Test that SardesTableWidget is initialized correctly."""
    tableview = tablewidget.tableview
    horiz_header = tablewidget.tableview.horizontalHeader()
    model = tableview.model()

    # Assert that the content of the table is as expected.
    assert_frame_equal(tableview.model().dataf, TABLE_DATAF)
    assert tableview.visible_row_count() == len(TABLE_DATAF)
    assert (tablewidget.rowcount_label.text() ==
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
    assert tableview.visible_columns() == [
        'col0', 'col1', 'col2', 'col3', 'col4', 'col5']

    # Hide the second, third, and fourth columns of the table.
    for logical_index in [1, 2, 3]:
        action = tableview._toggle_column_visibility_actions[logical_index]
        action.toggle()

        assert not action.isChecked()
        assert horiz_header.isSectionHidden(logical_index)
    assert tableview.hidden_column_count() == 3
    assert tableview.visible_column_count() == NCOL - 3
    assert tableview.visible_columns() == ['col0', 'col4', 'col5']

    # Toggle back the visibility of the second column.
    action = tableview._toggle_column_visibility_actions[1]
    action.toggle()
    assert action.isChecked()
    assert not horiz_header.isSectionHidden(1)
    assert tableview.hidden_column_count() == 2
    assert tableview.visible_column_count() == NCOL - 2
    assert tableview.visible_columns() == ['col0', 'col1', 'col4', 'col5']

    # Restore column visibility with action 'Show all'.
    menu = tablewidget._column_options_button.menu()
    menu.actions()[1].trigger()
    for action in tableview._toggle_column_visibility_actions:
        assert action.isChecked()
    for logical_index in range(tableview.column_count()):
        assert not horiz_header.isSectionHidden(logical_index)
    assert tableview.visible_column_count() == NCOL
    assert tableview.hidden_column_count() == 0
    assert tableview.visible_columns() == [
        'col0', 'col1', 'col2', 'col3', 'col4', 'col5']


def test_restore_columns_to_defaults(tablewidget, qtbot):
    """Test restoring the visibility and order of the columns."""
    tableview = tablewidget.tableview
    horiz_header = tableview.horizontalHeader()
    assert tableview.visible_columns() == [
        'col0', 'col1', 'col2', 'col3', 'col4', 'col5']

    # Move col2 to first position.
    horiz_header.moveSection(2, 0)
    assert horiz_header.logicalIndex(0) == 2
    assert horiz_header.logicalIndex(2) == 1
    assert tableview.visible_columns() == [
        'col2', 'col0', 'col1', 'col3', 'col4', 'col5']

    # Hide col1.
    logical_index = 1
    action = tableview._toggle_column_visibility_actions[logical_index]
    action.toggle()
    assert not action.isChecked()
    assert horiz_header.isSectionHidden(logical_index)
    assert tableview.visible_column_count() == NCOL - 1
    assert tableview.hidden_column_count() == 1
    assert tableview.visible_columns() == [
        'col2', 'col0', 'col3', 'col4', 'col5']

    # Restore columns to defaults with action 'Restore to defaults'.
    menu = tablewidget._column_options_button.menu()
    menu.actions()[0].trigger()
    assert horiz_header.logicalIndex(0) == 0
    assert horiz_header.logicalIndex(2) == 2
    assert action.isChecked()
    assert not horiz_header.isSectionHidden(logical_index)
    assert tableview.visible_column_count() == NCOL
    assert tableview.hidden_column_count() == 0
    assert tableview.visible_columns() == [
        'col0', 'col1', 'col2', 'col3', 'col4', 'col5']


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
    assert not tableview.model().is_data_clearable_at(model_index)
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
    mocker.patch.object(QMessageBox, 'exec_', return_value=QMessageBox.Cancel)
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


def test_edit_bool(tablewidget, qtbot, mocker):
    """
    Test editing the content of an cell containing an boolean.

    Regression test for cgq-qgc/sardes#557
    """
    tableview = tablewidget.tableview
    model_index = tableview.model().index(2, 1)

    # Select cell at model_index.
    qtbot.mouseClick(
        tableview.viewport(),
        Qt.LeftButton,
        pos=tableview.visualRect(model_index).center())
    assert model_index.data() == 'Yes'
    assert tableview.model().get_value_at(model_index) == True

    # Clear the value in the current cell.
    qtbot.keyPress(tableview, Qt.Key_Delete)
    assert model_index.data() == ''
    assert pd.isnull(tableview.model().get_value_at(model_index))

    # Save edits.
    mocker.patch.object(QMessageBox, 'exec_', return_value=QMessageBox.Cancel)
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
    item_delegate.editor.setCurrentIndex(1)
    qtbot.keyPress(item_delegate.editor, Qt.Key_Enter)
    assert model_index.data() == 'No'
    assert tableview.model().get_value_at(model_index) == False


def test_clearing_required_cell(tablewidget, qtbot):
    """
    Test clearing the content of cell that required a non null value.
    """
    tableview = tablewidget.tableview
    model_index = tableview.model().index(0, 0)
    assert tableview.model().is_data_required_at(model_index)
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
    assert not tableview.model().is_data_required_at(model_index)
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


def test_add_new_empty_row(tablewidget, qtbot, mocker, TABLE_DATAF):
    """
    Test that adding a new empty row to the table is working as expected.
    """
    tableview = tablewidget.tableview
    selection_model = tablewidget.tableview.selectionModel()
    assert len(TABLE_DATAF) == 3
    for i in range(3):
        # Assert that the first three rows are not new.
        assert not tableview.model().is_new_row_at(
            tableview.model().index(i, 0))

    # Add 3 new rows.
    for i in range(3):
        qtbot.keyPress(tableview, Qt.Key_Plus, modifier=Qt.ControlModifier)

        # Assert that each new row added is indeed considered as a new row.
        assert tableview.model().is_new_row_at(
            tableview.model().index(i + 3, 0))

    assert tableview.row_count() == 6
    assert len(TABLE_DATAF) == 3
    assert selection_model.currentIndex().isValid()
    assert selection_model.currentIndex() == tableview.model().index(5, 0)

    # Undo the last row added.
    tableview.undo_edits_action.trigger()
    assert tableview.row_count() == 5
    assert len(TABLE_DATAF) == 3
    assert selection_model.currentIndex().isValid()
    assert selection_model.currentIndex() == tableview.model().index(4, 0)

    # Save the results. A 'Save edits error' message should pop up because
    # values in 'Column #0' cannot be null.
    qmsgbox_patcher = mocker.patch.object(
        QMessageBox, 'exec_', return_value=QMessageBox.Ok)
    qtbot.keyPress(tablewidget, Qt.Key_Enter, modifier=Qt.ControlModifier)
    qtbot.wait(100)

    assert qmsgbox_patcher.call_count == 1
    assert tableview.row_count() == 5
    assert len(TABLE_DATAF) == 3

    # Edit the value in the column to a non null value and try to save the
    # table edits again.
    tableview.model().set_data_edit_at(
        tableview.model().index(3, 0), 'new_value_row3')
    tableview.model().set_data_edit_at(
        tableview.model().index(4, 0), 'new_value_row4')

    qmsgbox_patcher.return_value = QMessageBox.Save
    qtbot.keyPress(tablewidget, Qt.Key_Enter, modifier=Qt.ControlModifier)
    qtbot.wait(100)

    assert qmsgbox_patcher.call_count == 2
    assert tableview.row_count() == 5
    assert len(TABLE_DATAF) == 5


def test_append_row(tablewidget, qtbot, mocker, TABLE_DATAF):
    """
    Test that appending one or more new rows at the end of the data
    using some provided values is working as expecteds.
    """
    tableview = tablewidget.tableview
    selection_model = tablewidget.tableview.selectionModel()
    assert tableview.row_count() == len(TABLE_DATAF) == 3

    new_values = [
        {'col0': 'str4', 'col1': True, 'col2': 4.567,
         'col3': 123, 'col4': 'not editable', 'col5': None},
        {'col0': 'str5', 'col1': False, 'col2': 4.567,
         'col3': 9, 'col4': 'not editable', 'col5': None},
        ]

    # Append 2 new row to the table.
    tablewidget.tableview._append_row(new_values)
    assert tableview.row_count() == 5
    assert len(TABLE_DATAF) == 3
    assert selection_model.currentIndex().isValid()
    assert selection_model.currentIndex() == tableview.model().index(3, 0)

    for i in range(2):
        for j in range(6):
            model_index = tablewidget.model().index(i + 3, j)
            assert (tablewidget.model().get_value_at(model_index) ==
                    new_values[i][COLUMNS[j]])

            # Assert that each new row that was appended to the table is
            # considered as a new row in the model.
            assert tableview.model().is_new_row_at(model_index)

    # Undo the last operation.
    tablewidget.tableview.undo_edits_action.trigger()
    assert tableview.row_count() == len(TABLE_DATAF) == 3
    assert selection_model.currentIndex().isValid()
    assert selection_model.currentIndex() == tableview.model().index(2, 0)

    # Append back the 2 new rows and save the results.
    tablewidget.tableview._append_row(new_values)
    mocker.patch.object(QMessageBox, 'exec_', return_value=QMessageBox.Save)
    tablewidget.tableview.save_edits_action.trigger()
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
    selection_model = tableview.selectionModel()

    # Sort the data to cover the bug described in cgq-qgc/sardes#341.
    tableview.sort_by_column(3, 1)

    # Do some edits to the table's data programmatically in the first row
    # of the table.
    expected_data = ['new_str1', 'No', '1.234', '0']
    expected_value = ['new_str1', False, 1.234, 0]
    source_model_indexes = []
    for i in range(4):
        model_index = tableview.model().index(1, i)
        source_model_indexes.append(tableview.model().mapToSource(model_index))

        # Select and edit the content of the cell at the specified model
        # index. Note that the data of the table are going to be sorted
        # automatically when we edit the value in the fourth column.
        selection_model.setCurrentIndex(model_index, selection_model.Current)
        tableview.model().set_data_edit_at(model_index, expected_value[i])

        # Assert that the edit was applied as expected.
        model_index = tableview.model().mapFromSource(source_model_indexes[-1])
        assert model_index.data() == expected_data[i]
        assert tableview.model().get_value_at(model_index) == expected_value[i]
        assert tableview.model().data_edit_count()

    # Undo all remaining edits one by one with keyboard shortcut Ctrl+Z.
    original_data = ['str1', 'Yes', '1.111', '3', 'not editable']
    original_value = ['str1', True, 1.111, 3, 'not editable']
    for i in reversed(range(4)):
        qtbot.keyPress(tablewidget, Qt.Key_Z, modifier=Qt.ControlModifier)
        model_index = tableview.model().mapFromSource(source_model_indexes[i])

        # Assert that the cell where the edit was undone is selected
        # correctly as expected.
        assert selection_model.currentIndex() == model_index, i

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


def test_ensure_visible(tablewidget, qtbot, mocker):
    """
    Test that the method to ensure a cell at a given model index is
    visible is working as expected.

    See #cgq-qgc/sardes#506.
    """
    horiz_header = tablewidget.horizontalHeader()

    # Hide the third column of the table.
    col = 2
    action = tablewidget._toggle_column_visibility_actions[col]
    action.toggle()

    assert not action.isChecked()
    assert horiz_header.isSectionHidden(col)

    # Check that columns become visible again when we call
    # '_ensure_visible' on a cell that is in a hidden column.
    model_index = tablewidget.model().index(1, col)
    tablewidget._ensure_visible(model_index)
    qtbot.waitUntil(lambda: horiz_header.isSectionHidden(col) is False)


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


@flaky(max_runs=3)
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


def test_sorting_lettercase_and_accents(tablewidget, qtbot):
    """
    Test that sorting columns containing strings with capital letters and
    accented characters is working as expected.

    See cgq-qgc/sardes#543.
    """
    # Append new rows that contains strings with uppercase letters and
    # accented characters.
    new_values = [
        {'col0': 'à_new_string'},
        {'col0': 'e_new_string'},
        {'col0': 'É_new_string'},
        {'col0': 'E_new_string'},
        {'col0': 'A_new_string'},
        {'col0': 'é_new_string'},
        {'col0': 'a_new_string'},
        {'col0': 'À_new_string'}
        ]

    # Append 2 new row to the table.
    tablewidget.tableview._append_row(new_values)
    assert get_values_for_column(tablewidget.model().index(0, 0)) == [
        'str1', 'str2', 'str3',
        'à_new_string', 'e_new_string', 'É_new_string', 'E_new_string',
        'A_new_string', 'é_new_string', 'a_new_string', 'À_new_string']

    # Sort in ASCENDING order according to the first column.
    tablewidget.sort_by_column(0, 0)
    assert get_values_for_column(tablewidget.model().index(0, 0)) == [
        'A_new_string', 'a_new_string', 'à_new_string', 'À_new_string',
        'e_new_string', 'E_new_string', 'É_new_string', 'é_new_string',
        'str1', 'str2', 'str3']

    # Sort in DESCENDING order according to the first column.
    tablewidget.sort_by_column(0, 1)
    assert get_values_for_column(tablewidget.model().index(0, 0)) == [
        'str3', 'str2', 'str1',
        'É_new_string', 'é_new_string', 'e_new_string', 'E_new_string',
        'à_new_string', 'À_new_string', 'A_new_string', 'a_new_string']


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
    QApplication.clipboard().setText('test_test_test')

    # Try to copy something on the clipboard when nothing is selected
    # in the table.
    qtbot.keyPress(tableview, Qt.Key_C, modifier=Qt.ControlModifier)
    assert QApplication.clipboard().text() == 'test_test_test'

    # Do an invalid selection in the table and copy the selection to the
    # clipboard using the keyboard shorcut Ctrl+C.
    mocker.patch.object(QMessageBox, 'information')
    coord_to_select = [(0, 0), (0, 1), (2, 0), (2, 2)]
    for coord in coord_to_select:
        selection_model.select(model.index(*coord), selection_model.Select)
    qtbot.keyPress(tableview, Qt.Key_C, modifier=Qt.ControlModifier)

    assert QApplication.clipboard().text() == 'test_test_test'

    # Clear the selection of the table.
    qtbot.keyPress(tableview, Qt.Key_Escape)

    # Do a valid selection in the table and copy the selection to the
    # clipboard using the keyboard shorcut Ctrl+S.
    coord_to_select = [(0, 0), (0, 2), (2, 0), (2, 2)]
    for coord in coord_to_select:
        selection_model.select(model.index(*coord), selection_model.Select)
    qtbot.keyPress(tableview, Qt.Key_C, modifier=Qt.ControlModifier)
    assert QApplication.clipboard().text() == (
        'Column #0\tColumn #2\nstr1\t1.111\nstr3\t3.333\n')


def test_import_from_clipboard(tablewidget, qtbot, mocker, TABLE_DATAF):
    """
    Test that appending the Clipboard to a table widget works as expected.
    """
    tableview = tablewidget.tableview
    selection_model = tablewidget.tableview.selectionModel()
    horiz_header = tableview.horizontalHeader()
    
    print(tableview.model().columns())
    print(tableview.model().column_at(('col2')))
    return

    # We need to add the tool to import data from the clipboard explicitely.
    tablewidget.install_tool(
        ImportFromClipboardTool(tablewidget), after='copy_to_clipboard')

    # We sort the data according to col3, we then move col3 at the first
    # position and we hide col5.
    tableview.sort_by_column(3, 0)
    horiz_header.moveSection(3, 0)
    tableview._toggle_column_visibility_actions[5].toggle()
    assert tableview.visible_columns() == [
        'col3', 'col0', 'col1', 'col2', 'col4']

    # Add some data to the clipboard and import them into the table.
    mocker.patch.object(QMessageBox, 'warning', return_value=QMessageBox.Ok)

    pd.DataFrame(
        [[2, 'str4', 1, 9.543, 'some_string'],
         [34.25, 'str5', 'false', 'invalid float', 1.2345]],
        columns=['col3', 'col0', 'col1', 'col2', 'col4']
        ).to_clipboard(excel=True, index=False, na_rep='')
    tablewidget._tools['import_from_clipboard'].trigger()
    assert tableview.row_count() == 5
    assert selection_model.currentIndex() == tableview.model().index(1, 3)

    pd.DataFrame(
        [['invalid int', 'str6', 'invalid bool', 23, None]],
        columns=['col3', 'col0', 'col1', 'col2', 'col4']
        ).to_clipboard(excel=True, index=False, na_rep='')
    tablewidget._tools['import_from_clipboard'].trigger()
    assert tableview.row_count() == 6
    assert selection_model.currentIndex() == tableview.model().index(5, 3)

    # Assert that the data shown in the table and saved in the model
    # are as expected.
    expected_data = [
        ['1',  'str2', 'No', '2.222', 'not editable'],
        ['2', 'str4', 'Yes', '9.543', ''],
        ['3',  'str1', 'Yes', '1.111', 'not editable'],
        ['29', 'str3', 'Yes', '3.333', 'not editable'],
        ['34', 'str5', 'No', '', ''],
        ['', 'str6', '', '23.0', '']]
    for i in range(tableview.row_count()):
        assert tablewidget.get_data_for_row(i) == expected_data[i]

    expected_values = [
        [1,  'str2', False, 2.222, 'not editable'],
        [2, 'str4', True, 9.543, None],
        [3,  'str1', True, 1.111, 'not editable'],
        [29, 'str3', True, 3.333, 'not editable'],
        [34, 'str5', False, None, None],
        [None, 'str6', None, 23, None]]
    for i in range(tableview.row_count()):
        for x1, x2 in zip(
                tablewidget.get_values_for_row(i), expected_values[i]):
            assert are_values_equal(x1, x2), 'error on row {}'.format(i)


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
