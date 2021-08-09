# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports
from abc import ABC
import uuid

# ---- Third party imports
import pandas as pd

# ---- Local imports
from sardes.utils.data_operations import are_values_equal


# =============================================================================
# ---- Sardes Data and Edits
# =============================================================================
class SardesDataEditBase(ABC):
    """
    Basic functionality Sardes data edit class.

    WARNING: Don't override any methods or attributes present here unless you
    know what you are doing.
    """

    def __init__(self, index, column=None, parent=None):
        self.index = index
        self.column = column
        self.id = uuid.uuid4()
        self.parent = parent

    def undo(self):
        """Undo this data edit."""
        if self.parent is not None:
            self._undo()


class SardesDataEdit(SardesDataEditBase):
    """
    Sardes data edit class.

    All database accessors *must* inherit this class and reimplement
    its interface.
    """

    def _undo(self):
        """Undo this data edit."""
        pass


class NoDataEdit(SardesDataEdit):
    """
    A class to indicate that no edit have been done to the data since last
    save.
    """

    def __init__(self, index, column):
        super() .__init__(index, column)


class ValueChanged(SardesDataEdit):
    """
    A class that represents a change of a value at a given model index.
    """

    def __init__(self, index, column, edited_value, row, col, parent):
        super() .__init__(index, column, parent)
        self.edited_value = edited_value
        self.row = row
        self.col = col
        self.previous_value = self.parent.data.iat[row, col]

        if self.row not in self.parent._new_rows:
            # Update the list of original values that have been edited.
            # We store the original values in an independent list for
            # performance reasons when displaying the data in a tableview.
            if (row, col) in self.parent._original_data.index:
                original_value = self.parent._original_data.loc[
                    (row, col), 'value']
                self.parent._original_data.drop((row, col), inplace=True)
            else:
                original_value = self.parent.data.iat[row, col]

            # We only track edited values that differ from their corresponding
            # original value (the value that is saved in the database).
            # This allow to take into account the situation where an edited
            # value is edited back to its original value.
            if not are_values_equal(original_value, edited_value):
                self.parent._original_data.loc[
                    (row, col), 'value'] = original_value

        # We apply the new value to the data.
        self.parent.data.iat[row, col] = edited_value

    def type(self):
        """
        Return an integer that indicates the type of data edit this
        edit correspond to, as defined in :class:`SardesTableModelBase`.
        """
        return SardesTableData.ValueChanged

    def _undo(self):
        """
        Undo this value changed edit.
        """
        if self.row not in self.parent._new_rows:
            # Update the list of original values that have been edited.
            if (self.row, self.col) in self.parent._original_data.index:
                original_value = self.parent._original_data.loc[
                    (self.row, self.col), 'value']
                self.parent._original_data.drop(
                    (self.row, self.col), inplace=True)
            else:
                original_value = self.parent.data.iat[self.row, self.col]

            values_equal = are_values_equal(
                self.previous_value, original_value)
            if not values_equal:
                self.parent._original_data.loc[
                    (self.row, self.col), 'value'] = original_value

        # We apply the previous value to the data.
        self.parent.data.iat[self.row, self.col] = self.previous_value


class RowDeleted(SardesDataEdit):
    """
    A SardesDataEdit class used to delete one or more rows from a
    SardesTableData.

    Note that the rows are not actually deleted from the data. They are
    simply highlighted in red in the table until the edits are commited.
    """

    def __init__(self, index, row, parent):
        """
        Parameters
        ----------
        index : Index
            A pandas Index array that contains the list of values corresponding
            to the dataframe indexes of the rows that needs to be deleted
            from the parent SardesTableData.
        row : Index
            A pandas Index array that contains the list of integers
            corresponding to the logical indexes of the rows that needs to be
            deleted from the parent SardesTableData.
        parent : SardesTableData, optional
            A SardesTableData object where rows need to be deleted.
        """
        super() .__init__(index, None, parent)
        self.row = row
        self.parent._deleted_rows = self.parent._deleted_rows.append(self.row)

    def type(self):
        """
        Return an integer that indicates the type of data edit this
        edit correspond to, as defined in :class:`SardesTableModelBase`.
        """
        return SardesTableData.RowDeleted

    def _undo(self):
        """Undo this row deleted edit."""
        self.parent._deleted_rows = self.parent._deleted_rows.drop(self.row)


class RowAdded(SardesDataEdit):
    """
    A SardesDataEdit class to add one or more new rows to a SardesTableData.

    Note that new rows are always added at the end of the dataframe.
    """

    def __init__(self, index, values, parent):
        """
        Parameters
        ----------
        index : Index
            A pandas Index array that contains the indexes of the rows that
            needs to be added to the parent SardesTableData.
        values: list of dict
            A list of dict containing the values of the rows that needs to be
            added to the parent SardesTableData. The keys of the dict must
            match the parent SardesTableData columns.
        parent : SardesTableData
            A SardesTableData object where rows need to be added.
        """
        super() .__init__(index, None, parent)
        self.values = values
        self.row = pd.Index(
            [i + len(self.parent.data) for i in range(len(index))])

        # We update the table's variable that is used to track new rows.
        self.parent._new_rows = self.parent._new_rows.append(self.row)

        # We then add the new row to the data.
        self.parent.data = self.parent.data.append(pd.DataFrame(
            values, columns=self.parent.data.columns, index=index
            ))

    def __len__(self):
        """
        Return the number of rows that were added to the data with this edit.
        """
        return len(self.index)

    def type(self):
        """
        Return an integer that indicates the type of data edit this
        edit correspond to, as defined in :class:`SardesTableModelBase`.
        """
        return SardesTableData.RowAdded

    def _undo(self):
        """Undo this row added edit."""
        self.parent._new_rows = self.parent._new_rows.drop(self.row)

        # We remove the new row to the data.
        self.parent.data.drop(self.index, inplace=True)


class SardesTableData(object):
    """
    A container to hold data of a logical table and manage edits.
    """
    ValueChanged = 0
    RowAdded = 1
    RowRemoved = 2
    RowDeleted = 3

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

    def set(self, row, col, edited_value):
        """
        Store the new value at the given index and column and add the edit
        to the stack.
        """
        self._data_edits_stack.append(ValueChanged(
            self.data.index[row], self.data.columns[col],
            edited_value,
            row, col,
            parent=self
            ))
        return self._data_edits_stack[-1]

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
        self._data_edits_stack.append(RowAdded(index, values or [{}], self))
        return self._data_edits_stack[-1]

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
            self._data_edits_stack.append(RowDeleted(
                self.data.index[unique_rows], unique_rows, parent=self))
            return self._data_edits_stack[-1]

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
        Return a pandas DataFrame containing the rows that were
        added to the dataframe.
        """
        added_row_indexes = self.data.index[self._new_rows]

        # We remove new rows that were subsequently deleted from the
        # dataframe since there is no need to even add these to the database.
        added_row_indexes = added_row_indexes.drop(
            self.data.index[self._deleted_rows], errors='ignore')

        return self.data.loc[added_row_indexes]

    def edited_values(self):
        """
        Return a dictionary where keys correspond to the indexes of the rows
        that were edited in the data and values are dictionaries containing
        the values of the edited attributes on each corresponding row.
        """
        edited_values = {}
        for row, row_data in self._original_data.groupby(level=0):
            if row in self._deleted_rows:
                # Edits made to deleted rows are not tracked as net
                # edited values. Since these rows are going to be deleted
                # from the database anyway, there is not point in handling
                # these edits when commiting to the database.
                continue
            index = self.data.index[row]
            columns = self.data.columns[row_data.index.get_level_values(1)]
            row_edited_values = self.data.iloc[row][columns].to_dict()
            edited_values[index] = row_edited_values
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
    NCOL = 5
    COLUMNS = ['col{}'.format(i) for i in range(NCOL)]
    VALUES = [['str1', True, 1.111, 3, None],
              ['str2', False, 2.222, 1, None],
              ['str3', True, 3.333, 29, None]]

    dataset = pd.DataFrame(VALUES, columns=COLUMNS)
    dataset['col1'] = dataset['col1'].astype("Int64")
    dataset['col3'] = dataset['col3'].astype("Int64")

    tabledata = SardesTableData(dataset)

    tabledata.set(1, 0, 'edited_str2')
    tabledata.set(1, 2, 1.124)
    tabledata.set(1, 2, 1.124)
    tabledata.set(1, 3, None)

    print(tabledata, end='\n\n')
    print(tabledata.edited_values())
