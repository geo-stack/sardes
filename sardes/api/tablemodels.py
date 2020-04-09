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
from collections import OrderedDict
import uuid

# ---- Third party imports
import numpy as np
import pandas as pd
from qtpy.QtCore import (QAbstractTableModel, QModelIndex, Qt, QVariant,
                         Signal, QSortFilterProxyModel)
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QStyleOption

# ---- Local imports
from sardes.config.locale import _
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

    def __init__(self, index, column, edited_value, previous_value, row, col,
                 parent=None):
        super() .__init__(index, column, parent)
        self.previous_value = previous_value
        self.edited_value = edited_value
        self.row = row
        self.col = col

    def type(self):
        """
        Return an integer that indicates the type of data edit this
        edit correspond to, as defined in :class:`SardesTableModelBase`.
        """
        return SardesTableModelBase.ValueChanged

    def _undo(self):
        """Undo this value changed edit."""
        # Update the original data.
        if (self.row, self.col) in self.parent._original_data.index:
            original_value = self.parent._original_data.loc[
                (self.row, self.col), 'value']
            self.parent._original_data.drop((self.row, self.col), inplace=True)
        else:
            original_value = self.parent.data.iat[self.row, self.col]

        values_equal = are_values_equal(self.previous_value, original_value)
        if not values_equal or self.row in self.parent._new_rows:
            self.parent._original_data.loc[
                (self.row, self.col), 'value'] = original_value

        # We apply the previous value to the data.
        self.parent.data.iat[self.row, self.col] = self.previous_value


class RowDeleted(SardesDataEdit):
    """
    A class that represents on or more row(s) that were deleted from the data.
    """

    def __init__(self, index, row, col=0, parent=None):
        super() .__init__(index, None, parent)
        self.row = row
        self.col = col

    def type(self):
        """
        Return an integer that indicates the type of data edit this
        edit correspond to, as defined in :class:`SardesTableModelBase`.
        """
        return SardesTableModelBase.RowDeleted

    def _undo(self):
        """Undo this row deleted edit."""
        self.parent._deleted_rows = self.parent._deleted_rows.drop(self.row)


class RowAdded(SardesDataEdit):
    """
    A class that represents a new row added to the data.
    """

    def __init__(self, index, values, row, parent=None):
        super() .__init__(index, None, parent)
        self.values = values
        self.row = row
        self.col = 0

    def type(self):
        """
        Return an integer that indicates the type of data edit this
        edit correspond to, as defined in :class:`SardesTableModelBase`.
        """
        return SardesTableModelBase.RowAdded

    def _undo(self):
        """Undo this row added edit."""
        if self.parent is None:
            return

        # Update the original data.
        for col in range(len(self.parent.data.columns)):
            self.parent._original_data.drop((self.row, col), inplace=True)

        # We remove the row from the data.
        self.parent.data.drop(self.index, inplace=True)


class SardesTableData(object):
    """
    A container to hold data of a logical table and manage edits.
    """

    def __init__(self, data):
        self.data = data.copy()

        # A list containing the edits made by the user to the data
        # in chronological order.
        self._data_edits_stack = []

        self._new_rows = []
        self._deleted_rows = pd.Index([])

        # A pandas multiindex dataframe that contains the original data at
        # the rows and columns where the data was edited. This is tracked
        # independently of the data edits stack for performance purposes
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

    def set(self, row, col, edited_value):
        """
        Store the new value at the given index and column and add the edit
        to the stack.
        """
        previous_value = self.data.iat[row, col]
        self._data_edits_stack.append(ValueChanged(
            self.data.index[row], self.data.columns[col],
            edited_value, previous_value,
            row, col,
            parent=self
            ))

        # We update the list of original data. We store this in an independent
        # list for performance reasons when displaying the data in a GUI.
        if (row, col) in self._original_data.index:
            original_value = self._original_data.loc[(row, col), 'value']
            self._original_data.drop((row, col), inplace=True)
        else:
            original_value = self.data.iat[row, col]

        if original_value != edited_value:
            self._original_data.loc[(row, col), 'value'] = original_value

        # We apply the new value to the data.
        self.data.iat[row, col] = edited_value

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

    def add_row(self, new_index, values={}):
        """
        Add a new row with the provided values at the end of the data.
        """
        row = len(self.data)
        self._new_rows.append(row)
        self._data_edits_stack.append(
            RowAdded(new_index, values, row, parent=self))

        # We need to add each column of the new row to the orginal data so
        # that they are highlighted correctly in the table.
        for col in range(len(self.data.columns)):
            self._original_data.loc[(row, col), 'value'] = values.get(
                self.data.columns[col], None)

        # We add the new row to the data.
        self.data = self.data.append(pd.DataFrame(
            values, columns=self.data.columns, index=[new_index]))

        return self._data_edits_stack[-1]

    def delete_row(self, rows):
        """
        Delete the rows at the given row indexes from data.

        Parameters
        ----------
        rows: list of int
            An list of row logical indexes that need to be deleted from
            the data.
        """
        unique_rows = pd.Index(rows)
        unique_rows = unique_rows[~unique_rows.isin(self._deleted_rows)]
        if not unique_rows.empty:
            self._deleted_rows = self._deleted_rows.append(unique_rows)
            self._data_edits_stack.append(RowDeleted(
                self.data.index[unique_rows], unique_rows, parent=self))
            return self._data_edits_stack[-1]

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
        return bool(len(self._original_data) + len(self._deleted_rows))

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

    def is_value_edited_at(self, row, col):
        """
        Return whether edits were made at the specified model index
        since last save.
        """
        return (row, col) in self._original_data.index

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


# =============================================================================
# ---- Sardes Table Models
# =============================================================================
class SardesTableModelBase(QAbstractTableModel):
    """
    Basic functionality for Sardes table models.

    WARNING: Don't override any methods or attributes present here unless you
    know what you are doing.
    """
    sig_data_edited = Signal(object)
    sig_data_about_to_be_updated = Signal()
    sig_data_updated = Signal()
    sig_data_about_to_be_saved = Signal()
    sig_data_saved = Signal()
    sig_columns_mapper_changed = Signal()

    ValueChanged = 0
    RowAdded = 1
    RowRemoved = 2
    RowDeleted = 3

    def __init__(self, table_title='', table_id='', data_columns_mapper=[]):
        """
        Parameters
        ----------
        table_title : str
            The label that will be used to reference this table in the GUI.
        table_id : str
            A unique ID that will be used to reference this table in the code
            and in the user configurations.
        data_columns_mapper : list of tuple
            A list of tuple that maps the keys of the columns dataframe
            with their corresponding human readable label to use in the GUI.
            The default is [].
        """
        super().__init__()
        self._table_title = table_title
        self._table_id = table_id
        self._data_columns_mapper = OrderedDict(data_columns_mapper)

        # The sardes table data object that is used to store the table data
        # and handle edits.
        self._datat = None

        # A pandas dataframe containing the data that need to be shown in the
        # table, including the data edits.
        self.visual_dataf = None

        # A dictionary containing the dataframes of all the librairies
        # required by this table to display its data correctly.
        self.libraries = {}

        # Setup the data.
        self.set_model_data(pd.DataFrame([]))

        # The manager that handle fetching data and pushing data edits to
        # the database.
        self.db_connection_manager = None

    # ---- Columns
    @property
    def columns(self):
        """
        Return the list of keys used to reference the columns in this
        model's data.
        """
        return list(self._data_columns_mapper.keys())

    def columnCount(self, parent=QModelIndex()):
        """Return the number of columns in this model's data."""
        return len(self.columns)

    # ---- Horizontal Headers
    @property
    def horizontal_header_labels(self):
        """
        Return the list of labels that need to be displayed for each column
        of the table's horizontal header.
        """
        return list(self._data_columns_mapper.values())

    def get_horizontal_header_label_at(self, column_or_index):
        """
        Return the text of the label to display in the horizontal
        header for the key or logical index associated
        with the column.
        """
        return self._data_columns_mapper[
            column_or_index if isinstance(column_or_index, str) else
            self.columns[column_or_index]
            ]

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Qt method override."""
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self.get_horizontal_header_label_at(section)
            elif orientation == Qt.Vertical:
                return section + 1
        elif role == Qt.ToolTipRole:
            if orientation == Qt.Horizontal:
                return self.get_horizontal_header_label_at(section)
        return QVariant()

    # ---- Table data
    @property
    def dataf(self):
        """
        Return the pandas dataframe of the sardes table data object.
        """
        return self._datat.copy()

    def clear_data(self):
        """
        Clear the data of this model.
        """
        self.set_model_data(pd.DataFrame([]))
        for lib_name in self.libraries.keys():
            self.set_model_library(pd.DataFrame([]), lib_name)

    def set_model_data(self, dataf, dataf_columns_mapper=None):
        """
        Set the content of this table model to the data contained in dataf.

        Parameters
        ----------
        dataf: :class:`pd.DataFrame`
            A pandas dataframe containing the data or a library needed by this
            table model.

            Note that the column labels of the dataframe must match the
            values that are mapped in _data_columns_mapper.
        """
        self.beginResetModel()

        if dataf_columns_mapper is not None:
            self._data_columns_mapper = OrderedDict(dataf_columns_mapper)

        # Add missing columns to the dataframe and reorder columns to
        # mirror the column logical indexes of the table model so that we
        # can access them with pandas iloc.
        for column in self.columns:
            if column not in dataf.columns:
                dataf[column] = None
        dataf = dataf[self.columns]

        self._datat = SardesTableData(dataf)
        self.endResetModel()
        self._update_visual_data()
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.rowCount() - 1, self.columnCount() - 1)
            )
        self.modelReset.emit()

        if dataf_columns_mapper is not None:
            self.sig_columns_mapper_changed.emit()

    def set_model_library(self, dataf, name):
        """
        Set the data for the given library name and update the model.
        """
        self.libraries[name] = dataf
        self._update_visual_data()
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.rowCount() - 1, self.columnCount() - 1)
            )

    def rowCount(self, *args, **kargs):
        """Qt method override. Return the number visible rows in the table."""
        return len(self._datat)

    def data(self, index, role=Qt.DisplayRole):
        """Qt method override."""
        if role in [Qt.DisplayRole, Qt.ToolTipRole]:
            value = self.get_visual_data_at(index)
            if pd.isnull(value) or value in ['NaT']:
                value = ''
            elif pd.api.types.is_bool(value):
                value = _('Yes') if value else _('No')
            else:
                value = str(value)
            return value
        elif role == Qt.ForegroundRole:
            return QVariant()
        elif role == Qt.BackgroundRole:
            if self.is_data_deleted_at(index):
                return QColor('#FF9999')
            elif self.is_data_edited_at(index):
                return QColor('#CCFF99')
            else:
                return QStyleOption().palette.base().color()
        else:
            return QVariant()

    def flags(self, model_index):
        """Qt method override."""
        if self.is_data_deleted_at(model_index):
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        else:
            return Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable

    def get_visual_data_at(self, model_index):
        """
        Return the value to display in the table at the given model index.
        """
        return self.visual_dataf.iat[model_index.row(), model_index.column()]

    def get_value_at(self, model_index):
        """
        Return the value of the model's data at the specified model index.
        """
        return self._datat.get(model_index.row(), model_index.column())

    def is_value_in_column(self, model_index, value):
        """
        Check if the specified value is in the data of this model at the
        column specified by the model index.
        """
        return self._datat.is_value_in_column(model_index.column(), value)

    def is_null(self, model_index):
        """
        Return whether the value at the given model index is null.
        """
        return pd.isnull(self._datat.get(
            model_index.row(), model_index.column()))

    # ---- Visual Data
    def dataf_index_at(self, model_index):
        """
        Return the dataframe index corresponding to the specified visual
        model index.
        """
        return self.visual_dataf.index[model_index.row()]

    def dataf_column_at(self, model_index):
        """
        Return the dataframe column corresponding to the specified visual
        model index.
        """
        return self.columns[model_index.column()]

    def _update_visual_data(self):
        """
        Update the visual dataframe that is used to display the value in
        this tables.
        """
        self.visual_dataf = self._datat.copy()
        if self.visual_dataf.empty:
            return
        self.visual_dataf = self.logical_to_visual_data(self.visual_dataf)

    # ---- Data edits
    def data_edits(self):
        """
        Return a list of all edits made to the data since last save.
        """
        return self._datat.edits()

    def last_data_edit(self):
        """
        Return the last data edits made to the data since last save.
        """
        return self._datat.edits()[-1] if self.data_edit_count() else None

    def data_edit_count(self):
        """
        Return the number of edits in the stack.
        """
        return self._datat.edit_count()

    def has_unsaved_data_edits(self):
        """
        Return whether any edits were made to the table's data since last save.
        """
        return self._datat.has_unsaved_edits()

    def is_data_deleted_at(self, model_index):
        """
        Return whether the row at model index is deleted.
        """
        return self._datat.is_data_deleted_at(model_index.row())

    def is_data_edited_at(self, model_index):
        """
        Return whether edits were made at the specified model index
        since last save.
        """
        return self._datat.is_value_edited_at(
            model_index.row(), model_index.column())

    def cancel_data_edits(self):
        """
        Cancel all the edits that were made to the table data since last save.
        """
        self.beginResetModel()
        self._datat.cancel_edits()
        self._update_visual_data()
        self.endResetModel()
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.rowCount() - 1, self.columnCount() - 1)
            )
        self.sig_data_edited.emit(None)

    def set_data_edit_at(self, model_index, edited_value):
        """
        Store the value that was edited at the given model index.
        A signal is also emitted to indicate that the data were edited,
        so that the GUI can be updated accordingly.
        """
        data_edit = self._datat.set(
            model_index.row(), model_index.column(), edited_value)

        # We make the appropriate calls to update the model and GUI.
        self._update_visual_data()
        self.dataChanged.emit(model_index, model_index)
        self.sig_data_edited.emit(data_edit)

    def _create_new_row_index(self):
        """
        Return a new index that can be used to add a new item this
        model's data table.
        """
        if self.db_connection_manager is not None:
            try:
                return self.db_connection_manager.create_new_model_index(
                    self._table_id)
            except NotImplementedError:
                pass
        if str(self._datat.data.index.dtype) == 'object':
            return uuid.uuid4()
        elif str(self._datat.data.index.dtype) == 'int64':
            return max(self._datat.data.index) + 1

    def add_new_row(self, new_row_index=None):
        """
        Add a new empty at the end of the table.
        """
        self.beginInsertRows(
            QModelIndex(), len(self._datat), len(self._datat))

        if new_row_index is None:
            new_row_index = self._create_new_row_index()
        data_edit = self._datat.add_row(new_row_index)
        self._update_visual_data()
        self.endInsertRows()
        self.dataChanged.emit(
            self.index(self.rowCount() - 1, 0),
            self.index(self.rowCount() - 1, self.columnCount() - 1))

        # We make the appropriate calls to update the model and GUI.
        self.sig_data_edited.emit(data_edit)

    def delete_row(self, rows):
        """
        Delete rows at the specified row logical indexes.
        """
        data_edit = self._datat.delete_row(rows)
        if data_edit is not None:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(self.rowCount() - 1, self.columnCount() - 1))
            self.sig_data_edited.emit(data_edit)

    def undo_last_data_edit(self):
        """
        Undo the last data edits that was added to the stack.
        """
        last_edit = self.last_data_edit()
        if last_edit.type() == SardesTableModelBase.ValueChanged:
            self._datat.undo_edit()
            self._update_visual_data()
            self.dataChanged.emit(
                self.index(last_edit.row, last_edit.col),
                self.index(last_edit.row, last_edit.col),
                )
        elif last_edit.type() == SardesTableModelBase.RowAdded:
            self.beginRemoveRows(
                QModelIndex(), last_edit.row, last_edit.row)
            self._datat.undo_edit()
            self._update_visual_data()
            self.endRemoveRows()
            self.dataChanged.emit(
                self.index(last_edit.row, 0),
                self.index(last_edit.row, self.columnCount() - 1),
                )
        elif last_edit.type() == SardesTableModelBase.RowDeleted:
            self._datat.undo_edit()
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(self.rowCount() - 1, self.columnCount() - 1)
                )
        self.sig_data_edited.emit(last_edit)

    # ---- Database connection
    def set_database_connection_manager(self, db_connection_manager):
        """Setup the database connection manager for this table model."""
        self.db_connection_manager = db_connection_manager

    def update_data(self):
        """
        Update this model's data and library.
        """
        if self.db_connection_manager is not None:
            self.db_connection_manager.update_model(self._table_id)
        else:
            self._raise_db_connmanager_attr_error()

    def save_data_edits(self):
        """
        Save all data edits to the database.
        """
        if self.db_connection_manager is not None:
            self.db_connection_manager.save_model_edits(self._table_id)
        else:
            self._raise_db_connmanager_attr_error()

    @property
    def confirm_before_saving_edits(self):
        """
        Return wheter we should ask confirmation to the user before saving
        the data edits to the database.
        """
        if self.db_connection_manager is not None:
            return self.db_connection_manager._confirm_before_saving_edits
        else:
            self._raise_db_connmanager_attr_error()

    @confirm_before_saving_edits.setter
    def confirm_before_saving_edits(self, x):
        """
        Set wheter we should ask confirmation to the user before saving
        the data edits to the database.
        """
        if self.db_connection_manager is not None:
            self.db_connection_manager._confirm_before_saving_edits = bool(x)
        else:
            self._raise_db_connmanager_attr_error()

    def _raise_db_connmanager_attr_error(self):
        """
        Raise an attribute error after trying to access an attribute of the
        database connection manager while the later is None.
        """
        raise AttributeError(
            "The database connections manager for the table "
            "model {} is not set.".format(self._table_id))


class SardesTableModel(SardesTableModelBase):
    """
    An abstract table model to be used in a table view to display the data
    that are saved in the database.

    All table *must* inherit this class and reimplement its interface.

    """

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

    def create_delegate_for_column(self, view, column):
        """
        Create the item delegate that the view need to use when editing the
        data of this model for the specified column. By default, all columns
        are not editable. You need to expands this method to specify a
        different delegate to a column.
        """
        raise NotImplementedError

    def logical_to_visual_data(self, visual_dataf):
        """
        Transform logical data to visual data.

        Do any transformations to the source data so that they are displayed
        as you want in the table. Note that these transformations are
        applied to the visual dataframe, so that the source data are
        preserved in the process.

        For example, if you would like to display boolean values in a given
        column of the table as 'Yes' or 'No' strings, you would need to do:

        visual_dataf[column].replace(
            to_replace={True: 'Yes', False: 'No'}, inplace=False)
        """
        return visual_dataf


class SardesSortFilterModel(QSortFilterProxyModel):
    """
    A proxy model to sort and filter Sardes data.
    """
    sig_data_sorted = Signal()

    def __init__(self, source_model, multi_columns_sort=True):
        super().__init__()
        # Sorting and filtering.
        self._sort_by_columns = []
        self._columns_sort_order = []
        self._filter_by_columns = None
        self._proxy_dataf_index = []
        self._map_row_to_source = np.array([])
        self._map_row_from_source = np.array([])
        self._multi_columns_sort = multi_columns_sort

        # Setup source model.
        self.setSourceModel(source_model)
        source_model.sig_data_updated.connect(self.invalidate)
        source_model.dataChanged.connect(self.invalidate)

    def __getattr__(self, name):
        try:
            return super().__getattr__(name)
        except AttributeError:
            return getattr(self.sourceModel(), name)

    def rowCount(self, parent=QModelIndex()):
        """Return the number of rows in this model's data."""
        return len(self._proxy_dataf_index)

    def columnCount(self, parent=QModelIndex()):
        """Return the number of columns in this model's data."""
        return self.sourceModel().columnCount(parent)

    # ---- Invalidate
    def invalidate(self):
        """
        Invalidate the current sorting and filtering.
        """
        self._sort()
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.rowCount() - 1, self.columnCount() - 1)
            )

    def _sort(self):
        """
        Sort the visual data.

        https://stackoverflow.com/a/42039683/4481445
        """
        visual_dataf = self.sourceModel().visual_dataf
        if not self._sort_by_columns:
            # Clear sorting.
            self._proxy_dataf_index = visual_dataf.index.copy()
        else:
            # Sort the data by columns.
            self._proxy_dataf_index = visual_dataf.sort_values(
                by=[self.columns[index] for index in self._sort_by_columns],
                ascending=[not bool(v) for v in self._columns_sort_order],
                axis=0,
                inplace=False).index
        self._map_row_to_source = np.array([
            self.sourceModel().visual_dataf.index.get_loc(index) for
            index in self._proxy_dataf_index])
        self._map_row_from_source = np.array([
            self._proxy_dataf_index.get_loc(index) for
            index in self.sourceModel().visual_dataf.index])
        self.sig_data_sorted.emit()

    # ---- Public methods
    def sort(self, column_logical_index, sort_order):
        """
        Override Qt method so that sorting by columns is done with pandas
        instead, which is a lot faster for large datasets.

        https://bugreports.qt.io/browse/QTBUG-45208
        """
        if column_logical_index == -1:
            self._sort_by_columns = []
            self._columns_sort_order = []
        else:
            if not self._multi_columns_sort:
                self._sort_by_columns = []
                self._columns_sort_order = []
            else:
                try:
                    index = self._sort_by_columns.index(column_logical_index)
                except ValueError:
                    pass
                else:
                    del self._sort_by_columns[index]
                    del self._columns_sort_order[index]
            if sort_order != -1:
                self._sort_by_columns.insert(0, column_logical_index)
                self._columns_sort_order.insert(0, int(sort_order))
        self.invalidate()

    def get_columns_sorting_state(self):
        """
        Return the list of column logical indexes and the list of corresponding
        sort orders (0 for ascending, 1 for descending) by which the data
        were sorted in this model.
        """
        return self._sort_by_columns, self._columns_sort_order

    def set_columns_sorting_state(self, sort_by_columns, columns_sort_order):
        """
        Set the list of column logical indexes and the list of corresponding
        sort orders (0 for ascending, 1 for descending) by which the data
        need to be sorted in this model.

        Parameters
        ----------
        sort_by_columns : list of int
            A list of integers corresponding to the logical indexes of the
            columns by which the data need to be sorted.
        columns_sort_order : list of int
            A list of integers corresponding to the sort order (0 for ascending
            and 1 for descending) that need to be used to sort the data by
            the corresponding columns in sort_by_columns.
        """
        self._sort_by_columns = sort_by_columns
        self._columns_sort_order = columns_sort_order
        self.invalidate()

    # ---- Proxy to/from source mapping
    def mapToSource(self, proxy_index):
        """
        Return the model index in the source model that corresponds to the
        proxy_index in the proxy model.
        """
        if not proxy_index.isValid() or not len(self._proxy_dataf_index):
            return QModelIndex()

        try:
            source_index_row = self._map_row_to_source[proxy_index.row()]
        except IndexError:
            return QModelIndex()
        else:
            return self.sourceModel().index(
                source_index_row, proxy_index.column())

    def mapFromSource(self, source_index):
        """
        Return the model index in the proxy model that corresponds to the
        source_index from the source model.
        """
        if not source_index.isValid() or not len(self._proxy_dataf_index):
            return QModelIndex()

        proxy_index_row = self.mapRowFromSource(source_index.row())
        return (QModelIndex() if proxy_index_row is None else
                self.index(proxy_index_row, source_index.column()))

    def mapRowFromSource(self, source_row):
        """
        Return the row in the proxy model that corresponds to the
        row from the source model.
        """
        try:
            return self._map_row_from_source[source_row]
        except IndexError:
            return None

    def mapRowToSource(self, proxy_row):
        """
        Return the row in the source model that corresponds to the
        row from the proxy model.
        """
        try:
            return self._map_row_to_source[proxy_row]
        except IndexError:
            return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """
        Override Qt method so that the labels of the vertical header always
        start at 1 and are monotically increasing, regardless of the sorting
        and filtering applied to the data.
        """
        if role == Qt.DisplayRole and orientation == Qt.Vertical:
            return section + 1
        elif role == Qt.InitialSortOrderRole and orientation == Qt.Horizontal:
            try:
                index = self._sort_by_columns.index(section)
            except ValueError:
                return None
            else:
                return (Qt.AscendingOrder if
                        self._columns_sort_order[index] == 0 else
                        Qt.DescendingOrder)
        else:
            return self.sourceModel().headerData(section, orientation, role)

    def delete_row(self, proxy_rows):
        return self.sourceModel().delete_row(
            [self._map_row_to_source[row] for row in proxy_rows])

    def dataf_index_at(self, proxy_index):
        return self.sourceModel().dataf_index_at(
            self.mapToSource(proxy_index))

    def get_value_at(self, proxy_index):
        return self.sourceModel().get_value_at(
            self.mapToSource(proxy_index))

    def is_data_deleted_at(self, proxy_index):
        return self.sourceModel().is_data_deleted_at(
            self.mapToSource(proxy_index))

    def is_data_edited_at(self, proxy_index):
        return self.sourceModel().is_data_edited_at(
            self.mapToSource(proxy_index))

    def set_data_edit_at(self, proxy_indexes, edited_value):
        return self.sourceModel().set_data_edit_at(
            self.mapToSource(proxy_indexes), edited_value)

    def is_null(self, proxy_indexes):
        """
        Return whether the value at the given model index is null.
        """
        return self.sourceModel().is_null(self.mapToSource(proxy_indexes))
