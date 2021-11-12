# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Third party imports
import pandas as pd

# ---- Local imports
from sardes.api.tabledataedits import (
    TableDataEditTypes, ValueChanged, RowAdded, RowDeleted)


class SardesTableData(object):
    """
    A container to hold data of a logical table and manage edits.
    """
    ValueChanged = TableDataEditTypes.ValueChanged
    RowAdded = TableDataEditTypes.RowAdded
    RowDeleted = TableDataEditTypes.RowDeleted

    def __init__(self, data):
        self.data = data.copy()

        # A list containing the edits made by the user to the data
        # in chronological order.
        self._data_edits_stack = []

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
        return len(self.data)

    def __str__(self):
        return self.data.__str__()

    def set(self, row, col, value):
        """
        Store the new value at the given index and column and add the edit
        to the stack.
        """
        edit = ValueChanged(
            parent=self,
            index=self.data.index[row],
            column=self.data.columns[col],
            edited_value=value
            )
        edit.execute()
        self._data_edits_stack.append(edit)
        return edit

    def get(self, row, col=None):
        """
        Return the value at the given row and column indexes or the
        pandas series at the given row if no column index is given.
        """
        if col is not None:
            return self.data.iat[row, col]
        else:
            return self.data.iloc[row]

    def copy(self):
        """
        Return a copy of the data.
        """
        return self.data.copy()

    def add_row(self, index, values=None):
        """
        Add one or more new rows at the end of the data using the provided
        values.

        index : Index
            A pandas Index array that contains the indexes of the rows that
            needs to be added to the data.
        values: list of dict
            A list of dict containing the values of the rows that needs to be
            added to this SardesTableData. The keys of the dict must
            match the data..
        """
        edit = RowAdded(
            parent=self,
            index=index,
            values=values or [{}]
            )
        edit.execute()
        self._data_edits_stack.append(edit)
        return edit

    def delete_row(self, rows):
        """
        Delete the rows at the given row logical indexes from data.

        Parameters
        ----------
        rows: list of int
            A list of integers corresponding to the logical indexes of the
            rows that need to be deleted from the data.
        """
        unique_rows = pd.Index(rows)
        unique_rows = unique_rows[~unique_rows.isin(self._deleted_rows)]
        if not unique_rows.empty:
            # We only delete rows that are not already deleted.
            edit = RowDeleted(
                parent=self,
                index=self.data.index[unique_rows],
                row=unique_rows,
                )
            edit.execute()
            self._data_edits_stack.append(edit)
            return edit

    def deleted_rows(self):
        """
        Return a pandas Index array containing the indexes of the rows that
        were deleted in the dataframe.
        """
        deleted_rows = self.data.index[self._deleted_rows]

        # We remove rows that were added to the dataset since these were not
        # even added to the database yet.
        deleted_rows = deleted_rows.drop(
            self.data.index[self._new_rows], errors='ignore')

        return deleted_rows

    def added_rows(self):
        """
        Return a pandas dataframe containing the the new rows that were
        added to the data of this table.
        """
        added_row_indexes = self.data.index[self._new_rows]

        # We remove new rows that were subsequently deleted from the
        # dataframe since there is no need to even add these to the database.
        added_row_indexes = added_row_indexes.drop(
            self.data.index[self._deleted_rows], errors='ignore')

        return self.data.loc[added_row_indexes]

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
                self.data.index[orig_data_indexes.get_level_values(0)],
                self.data.columns[orig_data_indexes.get_level_values(1)]
                ]),
            columns=['edited_value'],
            dtype='object'
            )

        # We fetch the edited values from the data column by column.
        for col, data in edited_values.groupby(level=1):
            edited_values.loc[data.index, 'edited_value'] = self.data.loc[
                data.index.get_level_values(0), col].astype('object').array
            # Note that we need to use .array instead of .values to avoid
            # any unwanted dtype conversion from pandas to numpy when using
            # .values to access the data (ex. pd.datetime).
        return edited_values

    # ---- Edits
    def edits(self):
        """
        Return a list of all edits made to the data since last save.
        """
        return self._data_edits_stack

    def edit_count(self):
        """
        Return the number of edits in the stack.
        """
        return len(self._data_edits_stack)

    def has_unsaved_edits(self):
        """
        Return whether any edits were made to the table's data since last save.
        """
        return bool(len(self._original_data) +
                    len(self._deleted_rows) +
                    len(self._new_rows))

    def is_value_in_column(self, col, value):
        """
        Check if the specified value is in the given column of the data.
        """
        isin_indexes = self.data[self.data.iloc[:, col].isin([value])]
        return bool(len(isin_indexes))

    def is_data_deleted_at(self, row):
        """
        Return whether the row at row is deleted.
        """
        return row in self._deleted_rows

    def is_new_row_at(self, row):
        """
        Return whether the row at row is new.
        """
        return row in self._new_rows

    def is_value_edited_at(self, row, col):
        """
        Return whether edits were made at the specified model index
        since last save.
        """
        return row in self._new_rows or (row, col) in self._original_data.index

    def cancel_edits(self):
        """
        Cancel all the edits that were made to the table data since last save.
        """
        while self.edit_count():
            self.undo_edit()

    def undo_edit(self):
        """
        Undo the last data edit that was added to the stack.
        """
        if len(self._data_edits_stack):
            last_edit = self._data_edits_stack.pop(-1)
            last_edit.undo()


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
