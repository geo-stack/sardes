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
class TableDataEditBase(ABC):
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


class TableDataEdit(TableDataEditBase):
    """
    Sardes data edit class.

    All database accessors *must* inherit this class and reimplement
    its interface.
    """

    def _undo(self):
        """Undo this data edit."""
        pass


class NoDataEdit(TableDataEdit):
    """
    A class to indicate that no edit have been done to the data since last
    save.
    """

    def __init__(self, index, column):
        super() .__init__(index, column)


class ValueChanged(TableDataEdit):
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


class RowDeleted(TableDataEdit):
    """
    A TableDataEdit class used to delete one or more rows from a
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


class RowAdded(TableDataEdit):
    """
    A TableDataEdit class to add one or more new rows to a SardesTableData.

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
