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
from enum import Enum
from abc import ABC
import uuid

# ---- Third party imports
import pandas as pd

# ---- Local imports
from sardes.utils.data_operations import are_values_equal


class TableDataEditTypes(Enum):
    """
    An enum that list all types of edits that are supported by the
    TableData class.
    """
    ValueChanged = 0
    RowAdded = 1
    RowDeleted = 2


@dataclass
class TableDataEdit(ABC):
    """
    Sardes table data edit base class.

    All database accessors *must* inherit this class and reimplement
    its interface.

    Attributes
    ----------
    parent : SardesTableData
        A SardesTableData object on which the edit are executed.
    """
    parent: object
    id: uuid.UUID = field(default_factory=uuid.uuid4, init=False)

    def execute(self):
        pass

    def undo(self):
        """Undo this data edit."""
        pass

    @classmethod
    def type(cls):
        """
        Return the member of TableDataEditTypes corresponding to this
        table data edit class.
        """
        return getattr(TableDataEditTypes, cls.__name__)


@dataclass
class ValueChanged(TableDataEdit):
    """
    A class that represents a change of a value at a given model index.
    """
    index: object
    column: object
    edited_value: object
    row: int = field(init=False)
    col: int = field(init=False)
    previous_value: object = field(init=False)

    def __post_init__(self):
        self.row = self.parent.data.index.get_loc(self.index)
        self.col = self.parent.data.columns.get_loc(self.column)
        self.previous_value = self.parent.data.iat[self.row, self.col]

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
                original_value = self.parent.data.iat[self.row, self.col]

            # We only track edited values that differ from their corresponding
            # original value (the value that is saved in the database).
            # This allow to take into account the situation where an edited
            # value is edited back to its original value.
            if not are_values_equal(original_value, self.edited_value):
                self.parent._original_data.loc[
                    (self.row, self.col), 'value'] = original_value

        # We apply the new value to the data.
        self.parent.data.iat[self.row, self.col] = self.edited_value

    def undo(self):
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


@dataclass
class RowDeleted(TableDataEdit):
    """
    A TableDataEdit class used to delete one or more rows from a
    SardesTableData.

    Note that the rows are not actually deleted from the data. They are
    simply highlighted in red in the table until the edits are commited.

    Attributes
    ----------
    row : Index
        A pandas Index array that contains the list of integers
        corresponding to the logical indexes of the rows that needs to be
        deleted from the parent SardesTableData.
    index : Index
        A pandas Index array that contains the list of values corresponding
        to the dataframe indexes of the rows that needs to be deleted
        from the parent SardesTableData.
    """
    row: pd.Index
    index: pd.Index = field(init=False)

    def __post_init__(self):
        self.index = self.parent.data.index[self.row]

    def execute(self):
        self.parent._deleted_rows = self.parent._deleted_rows.append(self.row)

    def undo(self):
        self.parent._deleted_rows = self.parent._deleted_rows.drop(self.row)


@dataclass
class RowAdded(TableDataEdit):
    """
    A TableDataEdit class to add one or more new rows to a SardesTableData.

    Note that new rows are always added at the end of the dataframe.

    Attributes
    ----------
    index : Index
        A pandas Index array that contains the indexes of the rows that
        needs to be added to the parent SardesTableData.
    values: list of dict
        A list of dict containing the values of the rows that needs to be
        added to the parent SardesTableData. The keys of the dict must
        match the parent SardesTableData columns.
    """
    index: pd.Index
    values: list[dict]
    row: pd.Index = field(init=False)

    def __post_init__(self):
        self.row = pd.Index(
            [i + len(self.parent.data) for i in range(len(self.index))])

    def execute(self):
        # We update the table's variable that is used to track new rows.
        self.parent._new_rows = self.parent._new_rows.append(self.row)

        # We then add the new row to the data.
        self.parent.data = self.parent.data.append(
            pd.DataFrame(
                self.values,
                columns=self.parent.data.columns,
                index=self.index
                ))

    def __len__(self):
        """
        Return the number of rows that were added to the data with this edit.
        """
        return len(self.index)

    def undo(self):
        self.parent._new_rows = self.parent._new_rows.drop(self.row)

        # We remove the new row from the data.
        self.parent.data.drop(self.index, inplace=True)
