# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports
from __future__ import annotations
from dataclasses import dataclass, field

# ---- Third party imports
import pandas as pd

# ---- Local imports
from sardes.api.tableedits import TableEdit, TableEditsController
from sardes.utils.data_operations import are_values_equal


@dataclass
class EditValue(TableEdit):
    """
    An edit command to change the value at a given location in a Sardes
    table dataframe.
    """
    index: object
    column: object
    edited_value: object
    row: int = field(init=False)
    col: int = field(init=False)
    previous_value: object = field(init=False)

    def __post_init__(self):
        self.row = self.parent._data.index.get_loc(self.index)
        self.col = self.parent._data.columns.get_loc(self.column)
        self.previous_value = self.parent._data.iat[self.row, self.col]

    def execute(self):
        if self.row not in self.parent._new_rows:
            # Update the list of original values that have been edited.
            # We store the original values in an independent list for
            # performance reasons when displaying the data in a tableview.
            if (self.row, self.col) in self.parent._original_data.index:
                original_value = self.parent._original_data.loc[
                    (self.row, self.col), 'value']
                self.parent._original_data.drop(
                    (self.row, self.col), inplace=True)
            else:
                original_value = self.parent._data.iat[self.row, self.col]

            # We only track edited values that differ from their corresponding
            # original value (the value that is saved in the database).
            # This allow to take into account the situation where an edited
            # value is edited back to its original value.
            if not are_values_equal(original_value, self.edited_value):
                self.parent._original_data.loc[
                    (self.row, self.col), 'value'] = original_value

        # We apply the new value to the data.
        self.parent._data.iat[self.row, self.col] = self.edited_value

    def undo(self):
        if self.row not in self.parent._new_rows:
            # Update the list of original values that have been edited.
            if (self.row, self.col) in self.parent._original_data.index:
                original_value = self.parent._original_data.loc[
                    (self.row, self.col), 'value']
                self.parent._original_data.drop(
                    (self.row, self.col), inplace=True)
            else:
                original_value = self.parent._data.iat[self.row, self.col]

            values_equal = are_values_equal(
                self.previous_value, original_value)
            if not values_equal:
                self.parent._original_data.loc[
                    (self.row, self.col), 'value'] = original_value

        # We apply the previous value to the data.
        self.parent._data.iat[self.row, self.col] = self.previous_value

    def redo(self):
        self.execute()


@dataclass
class DeleteRows(TableEdit):
    """
    An edit command to delete one or more rows from a Sardes table dataframe.
    SardesTableData.

    Note that the rows are not actually deleted from the data. They are
    simply flagged as deleted until the edits are commited.

    Parameters
    ----------
    row : Index
        A pandas Index array that contains the list of integers
        corresponding to the logical indexes of the rows that needs to be
        deleted from the parent SardesTableData.

    Attributes
    ----------
    index : Index
        A pandas Index array that contains the list of values corresponding
        to the dataframe indexes of the rows that needs to be deleted
        from the parent SardesTableData.
    """
    row: pd.Index
    index: pd.Index = field(init=False)

    def __post_init__(self):
        self.index = self.parent._data.index[self.row]

    def execute(self):
        self.parent._deleted_rows = self.parent._deleted_rows.append(self.row)

    def undo(self):
        self.parent._deleted_rows = self.parent._deleted_rows.drop(self.row)

    def redo(self):
        self.execute()


@dataclass
class AddRows(TableEdit):
    """
    An edit command to add one or more new rows to a Sardes table dataframe.

    Note that new rows are always added at the end of the dataframe.

    Parameters
    ----------
    index : Index
        A pandas Index array that contains the indexes of the rows that
        needs to be added to the parent SardesTableData.
    values: list of dict
        A list of dict containing the values of the rows that needs to be
        added to the parent SardesTableData. The keys of the dict must
        match the parent SardesTableData columns.

    Attributes
    ----------
    row : Index
        A pandas Index array that contains the list of integers
        corresponding to the logical indexes of the rows that were added to
        the parent SardesTableData.
    """
    index: pd.Index
    values: list[dict]
    row: pd.Index = field(init=False)

    def __post_init__(self):
        self.row = pd.Index(
            [i + len(self.parent._data) for i in range(len(self.index))])

    def __len__(self):
        """Return the number of rows added by this edit."""
        return len(self.index)

    def execute(self):
        # We update the table's variable that is used to track new rows.
        self.parent._new_rows = self.parent._new_rows.append(self.row)

        # We then add the new row to the data.
        self.parent._data = self.parent._data.append(
            pd.DataFrame(
                self.values,
                columns=self.parent._data.columns,
                index=self.index
                ))

    def undo(self):
        self.parent._new_rows = self.parent._new_rows.drop(self.row)

        # We remove the new row from the data.
        self.parent._data.drop(self.index, inplace=True)

    def redo(self):
        self.execute()


class SardesTableData(object):
    """
    A wrapper around a pandas dataframe to hold the data of a Sarde table model
    and to add data edits management and changes tracking capabilities.

    Data edits are managed via a Command Design Pattern.
    See https://en.wikipedia.org/wiki/Command_pattern
    See also https://youtu.be/FM71_a3txTo

    Avoid applying changes to the wrapped dataframe outside of the public
    interface of SardesTableData unless you really know what you are doing.
    """
    EditValue = EditValue.type()
    AddRows = AddRows.type()
    DeleteRows = DeleteRows.type()

    def __init__(self, data):
        self._data = data.copy()

        self.edits_controller = TableEditsController()

        # Pandas Index of integers to track the logical indexes of rows that
        # were added or deleted to or from the dataframe.
        self._new_rows = pd.Index([])
        self._deleted_rows = pd.Index([])

        # A pandas multiindex dataframe that contains the original data at
        # the rows and columns where data was edited. This is tracked
        # independently from the data edits stack for performance purposes
        # when displaying the data in a GUI.
        self._original_data = pd.DataFrame(
            [], columns=['row', 'column', 'value'])
        self._original_data.set_index(
            'row', inplace=True, drop=True)
        self._original_data.set_index(
            'column', inplace=True, drop=True, append=True)

    def __len__(self):
        """Return the len of the data."""
        return len(self._data)

    def __str__(self):
        return self._data.__str__()

    @property
    def index(self):
        """Return a copy of the index of the wrapped dataframe."""
        return self._data.index.copy()

    @property
    def data(self):
        """Return a copy of the wrapped dataframe."""
        return self._data.copy()

    def copy(self):
        """Return a copy of the wrapped dataframe."""
        return self._data.copy()

    # ---- Data edits
    def set(self, row, col, value):
        """
        Store the new value at the given index and column and add the edit
        to the stack.
        """
        return self.edits_controller.execute(
            EditValue(
                parent=self,
                index=self._data.index[row],
                column=self._data.columns[col],
                edited_value=value)
            )

    def get(self, row, col=None):
        """
        Return the value at the given row and column indexes or the
        pandas series at the given row if no column index is given.
        """
        if col is not None:
            return self._data.iat[row, col]
        else:
            return self._data.iloc[row].copy()

    def add_row(self, index, values=None):
        """
        Add one or more new rows at the end of the data using the provided
        values.

        Parameters
        ----------
        index : Index
            A pandas Index array that contains the indexes of the rows that
            needs to be added to the data.
        values: list of dict
            A list of dict containing the values of the rows that needs to be
            added to this SardesTableData. The keys of the dict must
            match the data..
        """
        return self.edits_controller.execute(
            AddRows(
                parent=self,
                index=index,
                values=values or [{}])
            )

    def delete_row(self, rows):
        """
        Delete the rows at the given row logical indexes from data.

        Parameters
        ----------
        rows: list of int
            A list of integers corresponding to the logical indexes of the
            rows that need to be deleted from the data.
        """
        # We only delete rows that are not already deleted.
        unique_rows = pd.Index(rows)
        unique_rows = unique_rows[~unique_rows.isin(self._deleted_rows)]
        if not unique_rows.empty:
            return self.edits_controller.execute(
                DeleteRows(
                    parent=self,
                    row=unique_rows)
                )

    def cancel_edits(self):
        """
        Cancel all the edits that were made to the table data since last save.
        """
        while self.edit_count():
            self.undo_edit()

    def undo_edit(self):
        """Undo the last edit that was added to the stack."""
        return self.edits_controller.undo()

    def redo_edit(self):
        """Redo the last undone data edit."""
        return self.edits_controller.redo()

    # ---- Change tracking
    def deleted_rows(self):
        """
        Return a pandas Index array containing the indexes of the rows that
        were deleted in the dataframe.
        """
        deleted_rows = self._data.index[self._deleted_rows].copy()

        # We remove rows that were added to the dataset since these were not
        # even added to the database yet.
        deleted_rows = deleted_rows.drop(
            self._data.index[self._new_rows],
            errors='ignore')

        return deleted_rows

    def added_rows(self):
        """
        Return a pandas dataframe containing the the new rows that were
        added to the data of this table.
        """
        added_row_indexes = self._data.index[self._new_rows]

        # We remove new rows that were subsequently deleted from the
        # dataframe since there is no need to even add these to the database.
        added_row_indexes = added_row_indexes.drop(
            self._data.index[self._deleted_rows],
            errors='ignore')

        return self._data.loc[added_row_indexes].copy()

    def edited_values(self):
        """
        Return a multiindex dataframe containing the edited values at
        the corresponding indexes and columns of the dataframe.
        """
        # We remove deleted rows from the original data indexes.
        orig_data_indexes = self._original_data.index.drop(
            self._deleted_rows, level=0, errors='ignore')

        # We define a new multiindex dataframe to hold the edited values.
        edited_values = pd.DataFrame(
            data=[],
            index=pd.MultiIndex.from_arrays([
                self._data.index[orig_data_indexes.get_level_values(0)],
                self._data.columns[orig_data_indexes.get_level_values(1)]
                ]),
            columns=['edited_value'],
            dtype='object'
            )

        # We fetch the edited values from the data column by column.
        for col, data in edited_values.groupby(level=1):
            edited_values.loc[data.index, 'edited_value'] = (
                self._data.loc[data.index.get_level_values(0), col]
                .astype('object')
                .array)
            # Note that we need to use .array instead of .values to avoid
            # any unwanted dtype conversion from pandas to numpy when using
            # .values to access the data (ex. pd.datetime).
        return edited_values

    # ---- Utils
    def edits(self) -> list[TableEdit]:
        """
        Return a list of all edits made to the data since last save.
        """
        return self.edits_controller.undo_stack

    def edit_count(self) -> int:
        """Return the number of edits in the stack."""
        return self.edits_controller.undo_count()

    def undo_count(self) -> int:
        """Return the number of edits in the undo stack."""
        return self.edits_controller.undo_count()

    def redo_count(self) -> int:
        """Return the number of edits in the redo stack."""
        return self.edits_controller.redo_count()

    def has_unsaved_edits(self) -> bool:
        """
        Return whether any edits were made to the table's data since last save.
        """
        return bool(len(self._original_data) +
                    len(self._deleted_rows) +
                    len(self._new_rows))

    def is_value_in_column(self, col: int, value: object) -> bool:
        """
        Check if the specified value is in the given column of the data.
        """
        isin_indexes = self._data[self._data.iloc[:, col].isin([value])]
        return bool(len(isin_indexes))

    def is_data_deleted_at(self, row: int) -> bool:
        """
        Return whether the row at row is deleted.
        """
        return row in self._deleted_rows

    def is_new_row_at(self, row: int) -> bool:
        """
        Return whether the row at row is new.
        """
        return row in self._new_rows

    def is_value_edited_at(self, row: int, col: int) -> bool:
        """
        Return whether edits were made at the specified model index
        since last save.
        """
        return row in self._new_rows or (row, col) in self._original_data.index


if __name__ == '__main__':
    from datetime import datetime

    NCOL = 5
    COLUMNS = ['col{}'.format(i) for i in range(NCOL)]
    VALUES = [['str1', True, 1.111, 3, datetime(2001, 5, 12)],
              ['str2', False, 2.222, 1, datetime(2002, 5, 12)],
              ['str3', True, 3.333, 29, datetime(2003, 5, 12)]]

    dataset = pd.DataFrame(
        VALUES, columns=COLUMNS, index=['row0', 'row1', 'row2'])
    dataset['col1'] = dataset['col1'].astype("Int64")
    dataset['col3'] = dataset['col3'].astype("Int64")
    dataset['col4'] = pd.to_datetime(dataset['col4'])

    tabledata = SardesTableData(dataset)

    tabledata.set(1, 0, 'edited_str2')
    tabledata.set(1, 2, 1.124)
    tabledata.set(1, 2, 1.124)
    tabledata.set(1, 3, 4)
    tabledata.set(0, 4, datetime(2005, 5, 12))
    tabledata.set(2, 3, None)
    tabledata.set(1, 4, None)

    new_row = {'col0': 'str4', 'col1': True, 'col2': 4.444,
               'col3': 0, 'col4': datetime(2008, 8, 8)}
    tabledata.add_row(pd.Index(['new_row_index']), [new_row])

    edited_values = tabledata.edited_values()
    print(edited_values)
