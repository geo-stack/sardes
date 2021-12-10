# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the SardesTableData class.
"""

# ---- Third party imports
import pandas as pd
import pytest

# ---- Local imports
from sardes.api.tabledata import SardesTableData


COLUMNS = ['col0', 'col1', 'col2', 'col3', 'col4']
VALUES = [['str1', True, 1.111, 3, None],
          ['str2', False, 2.222, 1, None],
          ['str3', True, 3.333, 29, None]]


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dataset():
    dataset = pd.DataFrame(VALUES, columns=COLUMNS)
    dataset['col1'] = dataset['col1'].astype(pd.Int64Dtype())
    dataset['col3'] = dataset['col3'].astype(pd.Int64Dtype())
    return dataset


@pytest.fixture
def tabledata(dataset):
    tabledata = SardesTableData(dataset)

    assert tabledata.data.values.tolist() == VALUES

    assert tabledata.deleted_rows().empty
    assert tabledata.added_rows().empty
    assert tabledata.edited_values().empty

    assert tabledata.edits() == []
    assert tabledata.edit_count() == 0
    assert tabledata.has_unsaved_edits() is False

    yield tabledata

    # We cancel the edits and assert that we went back to the initial state.
    tabledata.cancel_edits()

    assert tabledata.data.values.tolist() == VALUES

    assert tabledata.deleted_rows().empty
    assert tabledata.added_rows().empty
    assert tabledata.edited_values().empty

    assert tabledata.edits() == []
    assert tabledata.edit_count() == 0
    assert tabledata.has_unsaved_edits() is False


# =============================================================================
# ---- Tests
# =============================================================================
def test_edit_data(tabledata):
    """
    Test that editing data is working as expected.
    """
    expected_values = [
        ['edited_str1', False, 1.111, 3, 'edited_none1'],
        ['edited_str2', False, 2.222, 1, 'edited_none2'],
        ['str3', True, 3.333, 29, None]]

    tabledata.set(0, 0, 'edited_str1')
    tabledata.set(0, 1, False)
    tabledata.set(0, 4, 'edited_none1')
    tabledata.set(1, 0, 'edited_str2')
    tabledata.set(1, 4, 'edited_none2')

    assert tabledata.edit_count() == 5
    assert tabledata.has_unsaved_edits() is True

    assert tabledata.data.values.tolist() == expected_values
    assert len(tabledata.deleted_rows()) == 0
    assert len(tabledata.added_rows()) == 0
    assert len(tabledata._original_data) == 5

    expected_values = {
        0: {'col0': 'edited_str1', 'col1': False, 'col4': 'edited_none1'},
        1: {'col0': 'edited_str2', 'col4': 'edited_none2'}}
    for index, values in tabledata.edited_values().groupby(level=0):
        values.index = values.index.droplevel(0)
        assert values['edited_value'].to_dict() == expected_values[index]


def test_edit_back_to_original(tabledata):
    """
    Test that editing back data to their original value is working
    as expected.
    """
    # Note that only edited data that are different than their original value
    # are actually considered as edits. This avoid making
    # unecessary operations when commiting edits to the database.

    tabledata.set(0, 0, 'edited_str1')

    assert tabledata.edit_count() == 1
    assert tabledata.has_unsaved_edits() is True
    assert len(tabledata._original_data) == 1

    expected_values = {0: {'col0': 'edited_str1'}}
    for index, values in tabledata.edited_values().groupby(level=0):
        values.index = values.index.droplevel(0)
        assert values['edited_value'].to_dict() == expected_values[index]

    tabledata.set(0, 0, 'str1')

    assert tabledata.edit_count() == 2
    assert tabledata.has_unsaved_edits() is False
    assert tabledata.edited_values().empty
    assert tabledata._original_data.empty


def test_add_row(tabledata):
    """
    Test that adding a new row is working as expected.
    """
    new_row = {'col0': 'str4', 'col1': True, 'col2': 4.444,
               'col3': 0, 'col4': 'note_4'}
    tabledata.add_row(pd.Index(['new_row_index']), [new_row])

    # We add new rows to the database.
    expected_values = [
        ['str1', True, 1.111, 3, None],
        ['str2', False, 2.222, 1, None],
        ['str3', True, 3.333, 29, None],
        ['str4', True, 4.444, 0, 'note_4']
        ]
    assert tabledata.data.values.tolist() == expected_values

    assert tabledata.edit_count() == 1
    assert tabledata.has_unsaved_edits() is True

    # Note that new rows are not considered as edited values.
    assert tabledata.edited_values().empty
    assert tabledata._original_data.empty
    assert tabledata._new_rows == pd.Index([3])

    expected_added_rows = {'new_row_index': new_row}
    assert tabledata.added_rows().index == list(expected_added_rows.keys())
    assert tabledata.added_rows().to_dict('index') == expected_added_rows


def test_delete_row(tabledata):
    """
    Test that deleting a row is working as expected.
    """
    expected_values = [
        ['str1', True, 1.111, 3, None],
        ['str2', False, 2.222, 1, None],
        ['str3', True, 3.333, 29, None],
        ]
    tabledata.delete_row(pd.Index([1]))
    assert tabledata.data.values.tolist() == expected_values

    assert tabledata.edit_count() == 1
    assert tabledata.has_unsaved_edits() is True

    # Note that deleted rows are not considered as edited values.
    assert tabledata.edited_values().empty
    assert tabledata._original_data.empty

    assert tabledata._deleted_rows == pd.Index([1])
    assert tabledata.deleted_rows() == pd.Index([1])


def test_delete_new_row(tabledata):
    """
    Test that deleting a new row is working as expected.
    """
    new_row = {'col0': 'str4', 'col1': True, 'col2': 4.444,
               'col3': 0, 'col4': 'note_4'}
    expected_values = [
        ['str1', True, 1.111, 3, None],
        ['str2', False, 2.222, 1, None],
        ['str3', True, 3.333, 29, None],
        ['str4', True, 4.444, 0, 'note_4']
        ]
    tabledata.add_row(pd.Index(['new_row_idx']), [new_row])
    tabledata.delete_row(pd.Index([3]))
    assert tabledata.data.values.tolist() == expected_values

    assert tabledata.edit_count() == 2
    assert tabledata.has_unsaved_edits() is True

    assert tabledata.edited_values().empty
    assert tabledata._original_data.empty

    assert tabledata._deleted_rows == pd.Index([3])
    assert tabledata.deleted_rows().empty

    assert tabledata._new_rows == pd.Index([3])
    assert tabledata.added_rows().empty


def test_delete_edited_row(tabledata):
    """
    Test that deleting an edited row is working as expected.
    """
    expected_values = [
        ['str1', True, 1.111, 3, None],
        ['edited_str2', False, 2.222, 1, None],
        ['str3', True, 3.333, 29, None]]
    tabledata.set(1, 0, 'edited_str2')
    tabledata.delete_row(pd.Index([1]))

    assert tabledata.data.values.tolist() == expected_values

    assert tabledata.edit_count() == 2
    assert tabledata.has_unsaved_edits() is True

    assert tabledata.edited_values().empty
    assert len(tabledata._original_data) == 1

    assert tabledata._deleted_rows == pd.Index([1])
    assert tabledata.deleted_rows() == pd.Index([1])


def test_edit_new_row(tabledata):
    """
    Test that editing a new row is working as expected.
    """
    new_row = {'col0': 'str4', 'col1': True, 'col2': 4.444,
               'col3': 0, 'col4': 'note_4'}
    expected_values = [
        ['str1', True, 1.111, 3, None],
        ['str2', False, 2.222, 1, None],
        ['str3', True, 3.333, 29, None],
        ['edited_str4', True, 4.444, 0, 'note_4']]
    tabledata.add_row(pd.Index([3]), [new_row])
    tabledata.set(3, 0, 'edited_str4')
    assert tabledata.data.values.tolist() == expected_values

    assert tabledata.edit_count() == 2
    assert tabledata.has_unsaved_edits() is True

    # Edits made to new rows are not tracked as edited values. These are
    # commited to the database as part of the operation to add the new rows.
    assert tabledata.edited_values().empty
    assert tabledata._original_data.empty

    assert tabledata._new_rows == pd.Index([3])
    assert tabledata.added_rows().to_dict('index') == {
        3: {'col0': 'edited_str4',
            'col1': True,
            'col2': 4.444,
            'col3': 0,
            'col4': 'note_4'}}
    assert tabledata.added_rows().index == [3]


def test_edit_deleted_row(tabledata):
    """
    Test that editing a deleted row is working as expected.
    """
    expected_values = [
        ['str1', True, 1.111, 3, None],
        ['edited_str2', False, 2.222, 1, None],
        ['str3', True, 3.333, 29, None]
        ]
    tabledata.delete_row(pd.Index([1]))
    tabledata.set(1, 0, 'edited_str2')
    assert tabledata.data.values.tolist() == expected_values

    assert tabledata.edit_count() == 2
    assert tabledata.has_unsaved_edits() is True

    # Edits made to deleted rows are not tracked as net edited values, since
    # these rows are going to be deleted from the database anyway, there is
    # not point in handling these edits.
    assert tabledata.edited_values().empty
    assert len(tabledata._original_data) == 1

    assert tabledata._deleted_rows == pd.Index([1])
    assert tabledata.deleted_rows() == pd.Index([1])


def test_undo_redo(tabledata):
    """
    Test that the undo and redo functionalities are working as expected.
    """
    # Add a new row.
    new_row = {'col0': 'str4', 'col1': True, 'col2': 4.444,
               'col3': 0, 'col4': 'note_4'}
    tabledata.add_row(pd.Index(['new_row_index']), [new_row])

    # Delete the second row.
    tabledata.delete_row(pd.Index([1]))

    # Edit a value on the first row.
    tabledata.set(0, 0, 'edited_str1')

    expected_values = [
        ['edited_str1', True, 1.111, 3, None],
        ['str2', False, 2.222, 1, None],
        ['str3', True, 3.333, 29, None],
        ['str4', True, 4.444, 0, 'note_4']
        ]

    assert tabledata.undo_count() == 3
    assert tabledata.redo_count() == 0
    assert tabledata.has_unsaved_edits() is True
    assert tabledata._deleted_rows == pd.Index([1])
    assert tabledata.data.values.tolist() == expected_values

    # Undo everything.
    tabledata.undo_edit()
    tabledata.undo_edit()
    tabledata.undo_edit()

    expected_values = [
        ['str1', True, 1.111, 3, None],
        ['str2', False, 2.222, 1, None],
        ['str3', True, 3.333, 29, None],
        ]

    assert tabledata.undo_count() == 0
    assert tabledata.redo_count() == 3
    assert tabledata.has_unsaved_edits() is False
    assert tabledata._deleted_rows.empty
    assert tabledata.data.values.tolist() == expected_values

    # Redo everything.
    tabledata.redo_edit()
    tabledata.redo_edit()
    tabledata.redo_edit()

    expected_values = [
        ['edited_str1', True, 1.111, 3, None],
        ['str2', False, 2.222, 1, None],
        ['str3', True, 3.333, 29, None],
        ['str4', True, 4.444, 0, 'note_4']
        ]

    assert tabledata.undo_count() == 3
    assert tabledata.redo_count() == 0
    assert tabledata.has_unsaved_edits() is True
    assert tabledata._deleted_rows == pd.Index([1])
    assert tabledata.data.values.tolist() == expected_values

    # Cancel all edits.
    tabledata.cancel_edits()

    expected_values = [
        ['str1', True, 1.111, 3, None],
        ['str2', False, 2.222, 1, None],
        ['str3', True, 3.333, 29, None],
        ]

    assert tabledata.undo_count() == 0
    assert tabledata.redo_count() == 3
    assert tabledata.has_unsaved_edits() is False
    assert tabledata._deleted_rows.empty
    assert tabledata.data.values.tolist() == expected_values


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
