# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports
from collections import OrderedDict
from dataclasses import dataclass, field
import uuid

# ---- Third party imports
import numpy as np
import pandas as pd
from qtpy.QtCore import (QAbstractTableModel, QModelIndex, Qt, QVariant,
                         Signal, QSortFilterProxyModel)
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QStyleOption

# ---- Local imports
from sardes.api.tabledata import SardesTableData


@dataclass
class SardesTableColumn():
    """A class for reprensenting a column in a Sardes table."""
    name: str
    header: str
    dtype: str
    notnull: bool = False
    unique: bool = False
    unique_subset: list = field(default_factory=list)
    editable: bool = True
    desc: str = None
    delegate: object = None
    delegate_options: dict = field(default_factory=dict)


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

    ValueChanged = SardesTableData.ValueChanged
    RowAdded = SardesTableData.RowAdded
    RowDeleted = SardesTableData.RowDeleted

    # =========================================================================
    # ---- API: Mandatory attributes
    # =========================================================================

    # Name of the table that will be used to refer to it in the code
    # and in the user configurations. This name must be unique and will
    # only be loaded once.
    __tablename__: str = None

    # The label that will be used to reference this table in the GUI.
    __tabletitle__: str = None

    # A list of sardes table columns representing the type of data this
    # table need to display.
    __tablecolumns__: list = None

    def __init__(self):
        super().__init__()

        self.BackgroundColorBase = QColor('white')
        self.BackgroundColorDeleted = QColor('#FF9999')
        self.BackgroundColorEdited = QColor('#CCFF99')

        self.__tablecolumns_loc__ = OrderedDict(
            [(column.name, column) for column in self.__tablecolumns__])

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

    def name(self):
        """Return the name of the table."""
        return self.__tablename__

    def title(self):
        """Return the title of the table."""
        return self.__tabletitle__

    def set_title(self, title):
        """Set the title of the table."""
        self.__tabletitle__ = title

    # ---- Columns
    def columns(self):
        """
        Return the list of columns that are defined for this table model.
        """
        return self.__tablecolumns__

    def set_columns(self, columns):
        """
        Define the column of this table.
        """
        self.__tablecolumns__ = columns
        self.__tablecolumns_loc__ = OrderedDict(
            [(column.name, column) for column in self.__tablecolumns__])

    def column_at(self, name):
        """Return the sardes table column corresponding to the given name."""
        return self.__tablecolumns_loc__[name]

    def column_names_headers_map(self):
        """
        Return a dictionary mapping columns name with their header.
        """
        return {column.name: column.header for column in self.__tablecolumns__}

    def columnCount(self, parent=QModelIndex()):
        """Return the number of columns in this model's data."""
        return len(self.__tablecolumns__)

    def column_names(self):
        """
        Return the list of names used to reference the columns in this
        model's data.
        """
        return [column.name for column in self.__tablecolumns__]

    def column_headers(self):
        """
        Return the list of labels that need to be displayed for each column
        of the table's horizontal header.
        """
        return [column.header for column in self.__tablecolumns__]

    def column_header_at(self, name):
        """
        Return the header of the sardes table column corresponding
        to the provided name.
        """
        return self.__tablecolumns_loc__[name].header

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Qt method override."""
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self.__tablecolumns__[section].header
            elif orientation == Qt.Vertical:
                return section + 1
        elif role == Qt.ToolTipRole:
            if orientation == Qt.Horizontal:
                return self.__tablecolumns__[section].header
        return QVariant()

    def create_delegate_for_column(self, table_view, column_name):
        """
        Create the item delegate that the view need to use when displaying and
        editing the data of this model for the specified column.
        """
        column = self.column_at(column_name)
        if column.delegate is None:
            return None
        else:
            return column.delegate(
                table_view,
                is_required=column.notnull,
                **column.delegate_options)

    # ---- Table data
    def tabledata(self):
        """
        Return the sardes table data of this table.
        """
        return self._datat

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

    def set_model_data(self, dataf, columns=None):
        """
        Set the content of this table model to the data contained in dataf.

        Parameters
        ----------
        dataf: :class:`pd.DataFrame`
            A pandas dataframe containing the data or a library needed by this
            table model.

            Note that the column labels of the dataframe must match the
            columns that are defined in columns.
        """
        self.beginResetModel()

        if columns is not None:
            self.set_columns(columns)

        # Add missing columns to the dataframe and reorder columns to
        # mirror the column logical indexes of the table model so that we
        # can access them with pandas iloc.
        for column_name in self.column_names():
            if column_name not in dataf.columns:
                dataf[column_name] = None
        dataf = dataf[self.column_names()]

        self._datat = SardesTableData(dataf)
        self.endResetModel()
        self._update_visual_data()
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.rowCount() - 1, self.columnCount() - 1)
            )
        self.modelReset.emit()

        if columns is not None:
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
            else:
                value = str(value)
            return value
        elif role == Qt.BackgroundRole:
            if self.is_data_deleted_at(index):
                return self.BackgroundColorDeleted
            elif self.is_data_edited_at(index):
                return self.BackgroundColorEdited
            else:
                return self.BackgroundColorBase
        else:
            return QVariant()

    def flags(self, model_index):
        """Qt method override."""
        if self.is_data_editable_at(model_index):
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable
        else:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable

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
        return self.column_names()[model_index.column()]

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
    def is_data_clearable_at(self, model_index):
        """
        Return whether the value of the cell at the specified model index
        is clearable or not.
        """
        return (
            not self.is_null(model_index) and
            self.is_data_editable_at(model_index) and
            not self.columns()[model_index.column()].notnull)

    def is_data_deleted_at(self, model_index):
        """
        Return whether the row at model index is deleted.
        """
        return self._datat.is_data_deleted_at(model_index.row())

    def is_data_editable_at(self, model_index):
        """
        Return whether the cell at the specified model index is editable.
        """
        return (
            self.columns()[model_index.column()].editable and
            not self.is_data_deleted_at(model_index))

    def is_data_edited_at(self, model_index):
        """
        Return whether edits were made at the specified model index
        since last save.
        """
        return self._datat.is_value_edited_at(
            model_index.row(), model_index.column())

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

    def is_new_row_at(self, model_index):
        """
        Return whether the row at model index is new.
        """
        return self._datat.is_new_row_at(model_index.row())

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

    def clear_model_data_at(self, model_index):
        """
        Set the data at the given provided model index to a null value.
        """
        if model_index.isValid() and self.is_data_clearable_at(model_index):
            self.set_data_edit_at(model_index, None)

    def create_new_row_index(self):
        """
        Return a new index that can be used to add a new item this
        model's data table.
        """
        if str(self._datat.data.index.dtype) == 'object':
            return uuid.uuid4()
        elif str(self._datat.data.index.dtype) == 'int64':
            return max(self._datat.data.index) + 1

    def add_new_row(self):
        """
        Add a new empty at the end of the table.
        """
        self.beginInsertRows(
            QModelIndex(), len(self._datat), len(self._datat))
        index = pd.Index([self.create_new_row_index()])
        data_edit = self._datat.add_row(index)
        self._update_visual_data()
        self.endInsertRows()
        self.dataChanged.emit(
            self.index(self.rowCount() - 1, 0),
            self.index(self.rowCount() - 1, self.columnCount() - 1))

        # We make the appropriate calls to update the model and GUI.
        self.sig_data_edited.emit(data_edit)

    def append_row(self, values):
        """
        Append one or more new rows at the end of the data using the provided
        values.

        values: list of dict
            A list of dict containing the values of the rows that needs to be
            added to this SardesTableData. The keys of the dict must
            match the data..
        """
        if not len(values):
            return

        self.beginInsertRows(
            QModelIndex(),
            len(self._datat),
            len(self._datat) + len(values) - 1)
        index = pd.Index(
            [self.create_new_row_index() for i in range(len(values))])
        data_edit = self._datat.add_row(index, values)
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

        Parameters
        ----------
        rows: list of int
            A list of integers corresponding to the logical indexes of the
            rows that need to be deleted from the data.
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
                QModelIndex(), min(last_edit.row), max(last_edit.row))
            self._datat.undo_edit()
            self._update_visual_data()
            self.endRemoveRows()
            self.dataChanged.emit(
                self.index(min(last_edit.row), 0),
                self.index(max(last_edit.row), self.columnCount() - 1),
                )
        elif last_edit.type() == SardesTableModelBase.RowDeleted:
            self._datat.undo_edit()
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(self.rowCount() - 1, self.columnCount() - 1)
                )
        self.sig_data_edited.emit(last_edit)


class SardesTableModel(SardesTableModelBase):
    """
    An abstract table model to be used in a table view to display the data
    that are saved in the database.

    All table *must* inherit this class and reimplement its interface.
    """

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
            to_replace={True: 'Yes', False: 'No'}, inplace=True)
        """
        return visual_dataf

    def check_data_edits(self):
        """
        Check that there is no issues with the data edits of this model.
        """
        raise NotImplementedError

    def save_data_edits(self):
        """
        Save all data edits to the database.
        """
        raise NotImplementedError

    def confirm_before_saving_edits(self):
        """
        Return wheter we should ask confirmation to the user before saving
        the data edits to the database.
        """
        raise NotImplementedError

    def set_confirm_before_saving_edits(self, x):
        """
        Set wheter we should ask confirmation to the user before saving
        the data edits to the database.
        """
        raise NotImplementedError


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
        self._proxy_dataf_index = pd.Index([])
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
                by=[self.column_names()[index] for index in
                    self._sort_by_columns],
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
        if not proxy_index.isValid() or self._proxy_dataf_index.empty:
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
        if not source_index.isValid() or self._proxy_dataf_index.empty:
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

    def is_data_editable_at(self, proxy_index):
        return self.sourceModel().is_data_editable_at(
            self.mapToSource(proxy_index))

    def is_data_clearable_at(self, proxy_index):
        return self.sourceModel().is_data_clearable_at(
            self.mapToSource(proxy_index))

    def is_data_deleted_at(self, proxy_index):
        return self.sourceModel().is_data_deleted_at(
            self.mapToSource(proxy_index))

    def is_new_row_at(self, proxy_index):
        return self.sourceModel().is_new_row_at(
            self.mapToSource(proxy_index))

    def is_data_edited_at(self, proxy_index):
        return self.sourceModel().is_data_edited_at(
            self.mapToSource(proxy_index))

    def set_data_edit_at(self, proxy_indexes, edited_value):
        return self.sourceModel().set_data_edit_at(
            self.mapToSource(proxy_indexes), edited_value)

    def clear_model_data_at(self, proxy_index):
        return self.sourceModel().clear_model_data_at(
            self.mapToSource(proxy_index))

    def is_null(self, proxy_indexes):
        """
        Return whether the value at the given model index is null.
        """
        return self.sourceModel().is_null(self.mapToSource(proxy_indexes))
