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

# ---- Third party imports
import pandas as pd
from qtpy.QtCore import (QAbstractTableModel, QModelIndex, Qt, QVariant,
                         Signal, QSortFilterProxyModel)
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QStyleOption

# ---- Local imports
from sardes.config.locale import _


class NoDataEdit(object):
    """
    A class to indicate that no edit have been done to the data since last
    save.
    """

    def __init__(self, index, column):
        super() .__init__()
        self.index = index
        self.column = column


class ValueChanged(object):
    """
    A class that represent a change of a value at a given model index.
    """

    def __init__(self, index, column, value, edited_value):
        super() .__init__()
        self.index = index
        self.column = column
        self.value = value
        self.edited_value = edited_value

    def type(self):
        """
        Return an integer that indicates the type of data edit this
        edit correspond to, as defined in :class:`SardesTableModelBase`.
        """
        return SardesTableModelBase.ValueChanged


class SardesTableModelBase(QAbstractTableModel):
    """
    Basic functionality for Sardes table models.

    WARNING: Don't override any methods or attributes present here unless you
    know what you are doing.
    """
    sig_data_edited = Signal(bool, bool)
    sig_data_about_to_be_updated = Signal()
    sig_data_updated = Signal()
    sig_data_about_to_be_saved = Signal()
    sig_data_saved = Signal()

    ValueChanged = 0
    RowAdded = 1
    RowRemoved = 2

    def __init__(self, db_connection_manager):
        super().__init__()
        self._data_columns_mapper = OrderedDict(self.__data_columns_mapper__)

        # A pandas dataframe containing the data that are shown in the
        # database.
        self.dataf = pd.DataFrame([])

        # A pandas dataframe containing the data that need to be shown in the
        # table, including the data edits.
        self.visual_dataf = pd.DataFrame([], columns=self.columns)

        # A dictionary containing the dataframes of all the librairies
        # required by this table to display its data correctly.
        self.libraries = {}

        # A list containing the names of the data that needs to be updated,
        # so that we can emit sig_data_updated only when all data have been
        # updated.
        self._data_that_need_to_be_updated = []

        # A list containing the edits made by the user to the
        # content of this table's model data in chronological order.
        self._data_edit_stack = []
        self._new_rows = []
        self._deleted_rows = []

        # A pandas dataframe that contains the edited values at their
        # corresponding data index and column.
        self._edited_dataf = pd.DataFrame(
            [], columns=['index', 'column', 'edited_value'])
        self._edited_dataf.set_index('index', inplace=True, drop=True)
        self._edited_dataf.set_index(
            'column', inplace=True, drop=True, append=True)

        # Sorting and filtering.
        self._filter_by_columns = None

        self.set_database_connection_manager(db_connection_manager)

    def set_database_connection_manager(self, db_connection_manager):
        """Setup the database connection manager for this table model."""
        self.db_connection_manager = db_connection_manager

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
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.get_horizontal_header_label_at(section)
        if role == Qt.DisplayRole and orientation == Qt.Vertical:
            return section + 1
        else:
            return QVariant()

    # ---- Table data
    def clear_data(self):
        """
        Clear the data of this model.
        """
        self._data_that_need_to_be_updated = self.req_data_names()
        for name in self.req_data_names():
            dataf = pd.DataFrame([])
            dataf.name = name
            self.set_model_data(dataf)

    def req_data_names(self):
        """
        Required the names of all data and libraries that this table
        requires.
        """
        return self.REQ_LIB_NAMES + [self.TABLE_DATA_NAME]

    def update_data(self, names):
        """
        Update this model's data and library according to the list of
        data name in names.
        """
        if not names:
            return

        self.sig_data_about_to_be_updated.emit()
        self._data_that_need_to_be_updated = names
        for name in names:
            self.db_connection_manager.get(
                name,
                callback=self.set_model_data,
                postpone_exec=True)
        self.db_connection_manager.run_tasks()

    def fetch_data(self):
        """
        Fetch the data and libraries for this model.
        """
        # Note that we need to fetch the libraries before we fetch the
        # table's data.
        self.update_data(self.REQ_LIB_NAMES + [self.TABLE_DATA_NAME])

    def set_model_data(self, dataf):
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
        if dataf.name == self.TABLE_DATA_NAME:
            self.beginResetModel()
            self.dataf = dataf
            self.visual_dataf = dataf.copy()

            # Add missing columns to the dataframe.
            for column in self.columns:
                if column not in self.dataf.columns:
                    self.dataf[column] = None

            self._edited_dataf.drop(self._edited_dataf.index, inplace=True)
            self._data_edit_stack = []
            self._new_rows = []
            self._deleted_rows = []
            self._update_visual_data()

            self.endResetModel()
            self.sig_data_edited.emit(False, False)
        elif dataf.name in self.REQ_LIB_NAMES:
            self.libraries[dataf.name] = dataf
            self._update_visual_data()

        # Update the state of data update and emit a signal if the updating
        # is completed.
        self._data_that_need_to_be_updated.remove(dataf.name)
        if not self._data_that_need_to_be_updated:
            self.sig_data_updated.emit()

    def rowCount(self, *args, **kargs):
        """Qt method override. Return the number visible rows in the table."""
        return len(self.visual_dataf)

    def data(self, index, role=Qt.DisplayRole):
        """Qt method override."""
        if role in [Qt.DisplayRole, Qt.ToolTipRole]:
            value = self.visual_dataf.iloc[
                index.row(),
                self.visual_dataf.columns.get_loc(self.dataf_column_at(index))
                ]
            if pd.isna(value) or value is None:
                value = ''
            elif pd.api.types.is_bool(value):
                value = _('Yes') if value else _('No')
            else:
                value = str(value)
            return value
        elif role == Qt.ForegroundRole:
            return QVariant()
        elif role == Qt.BackgroundRole:
            if self.is_data_edited_at(index):
                return QColor('#CCFF99')
            else:
                return QStyleOption().palette.base().color()
        else:
            return QVariant()

    def flags(self, model_index):
        """Qt method override."""
        return Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable

    def get_dataf_value_at(self, model_index):
        """
        Return the unedited value of the model's data at the specified model
        index.
        """
        try:
            return self.dataf.loc[self.dataf_index_at(model_index),
                                  self.dataf_column_at(model_index)]
        except KeyError:
            return None

    def get_value_at(self, model_index):
        """
        Return the edited, visible, value of the model's data at the
        specified model index.
        """
        # We check first if the data was edited by the user if 'ignore_edits'
        # is True.
        value = self.get_edited_data_at(model_index)
        if isinstance(value, NoDataEdit):
            # This means that the value was not edited by the user, so we
            # fetch the value directly from the model's data.
            value = self.get_dataf_value_at(model_index)
        return value

    def is_value_in_column(self, model_index, value):
        """
        Check if the specified value is in the data of this model at the
        column specified by the model index.
        """
        dataf_column = self.dataf_column_at(model_index)

        # First we check if value is found in the edited data.
        if any(self._edited_dataf
               .loc[(slice(None), slice(dataf_column)), 'edited_value']
               .isin([value])):
            return True
        else:
            # Else we check if the value is found in the unedited data
            # of this model's data.
            isin_indexes = self.dataf[self.dataf[dataf_column].isin([value])]
            return any([
                not self.is_data_edited_at(self.index(
                    self.dataf.index.get_loc(index), model_index.column()))
                for index in isin_indexes.index
                ])

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
        self.visual_dataf = self.dataf.copy()
        if self.dataf.empty:
            return

        # Fist we apply the edited values to the dataframe.
        for index, column in self._edited_dataf.index:
            self.visual_dataf.loc[index, column] = (
                self._edited_dataf.loc[(index, column), 'edited_value'])

        self.visual_dataf = self.logical_to_visual_data(self.visual_dataf)

        self.dataChanged.emit(
            self.index(0, 0),
            self.index(len(self.visual_dataf) - 1,
                       len(self.visual_dataf.columns) - 1)
            )

    # ---- Data edits
    @property
    def confirm_before_saving_edits(self):
        """
        Return wheter we should ask confirmation to the user before saving
        the data edits to the database.
        """
        return self.db_connection_manager._confirm_before_saving_edits

    @confirm_before_saving_edits.setter
    def confirm_before_saving_edits(self, x):
        """
        Set wheter we should ask confirmation to the user before saving
        the data edits to the database.
        """
        self.db_connection_manager._confirm_before_saving_edits = bool(x)

    def data_edit_count(self):
        """
        Return the number of edits in the stack.
        """
        return len(self._data_edit_stack)

    def has_unsaved_data_edits(self):
        """
        Return whether any edits were made to the table's data since last save.
        """
        return bool(len(self._edited_dataf))

    def is_data_edited_at(self, model_index):
        """
        Return whether edits were made at the specified model index
        since last save.
        """
        return (self.dataf_index_at(model_index),
                self.columns[model_index.column()]
                ) in self._edited_dataf.index

    def cancel_all_data_edits(self):
        """
        Cancel all the edits that were made to the table data since last save.
        """
        self._data_edit_stack = []
        self._edited_dataf.drop(self._edited_dataf.index, inplace=True)
        self._update_visual_data()
        self.sig_data_edited.emit(False, False)

    def get_edited_data_at(self, model_index):
        """
        Return the edited value, if any, that was made at the specified
        model index since last save.
        """
        dataf_index = self.dataf_index_at(model_index)
        dataf_column = self.dataf_column_at(model_index)
        try:
            return self._edited_dataf.loc[
                (dataf_index, dataf_column), 'edited_value']
        except KeyError:
            return NoDataEdit(dataf_index, dataf_column)

    def set_data_edits_at(self, model_indexes, edited_values):
        """
        Store the values that were edited at the specified model indexes.
        A signal is also emitted to indicate that the data were edited,
        so that the GUI can be updated accordingly.
        """
        if not isinstance(model_indexes, list):
            model_indexes = [model_indexes, ]
        if not isinstance(edited_values, list):
            edited_values = [edited_values, ]

        edits = []
        for model_index, edited_value in zip(model_indexes, edited_values):
            dataf_value = self.get_dataf_value_at(model_index)
            dataf_index = self.dataf_index_at(model_index)
            dataf_column = self.dataf_column_at(model_index)
            edits.append(ValueChanged(
                dataf_index, dataf_column, dataf_value, edited_value))

            # We add the model index to the list of indexes whose value have
            # been edited if the edited value differ from the value saved in
            # the model's data.
            if (dataf_index, dataf_column) in self._edited_dataf.index:
                self._edited_dataf.drop(
                    (dataf_index, dataf_column), inplace=True)
            if dataf_value != edited_value:
                self._edited_dataf.loc[(dataf_index, dataf_column),
                                       'edited_value'
                                       ] = edited_value
        # We store the edited values until it is commited and
        # saved to the database.
        self._data_edit_stack.append(edits)

        # We make the appropriate calls to update the model and GUI.
        self._update_visual_data()
        self.sig_data_edited.emit(
            self.has_unsaved_data_edits(), bool(self.data_edit_count()))

    def undo_last_data_edit(self):
        """
        Undo the last data edits that was added to the stack.
        An update of the view is forced if  update_model_view is True.
        """
        if len(self._data_edit_stack) == 0:
            return

        # Undo the last edits. Note that the last edits can comprise
        # more than one edit.
        last_edits = self._data_edit_stack.pop(-1)
        for last_edit in last_edits:
            if (last_edit.index, last_edit.column) in self._edited_dataf.index:
                self._edited_dataf.drop((last_edit.index, last_edit.column),
                                        inplace=True)

            # Check if there was a previous edit for this model index
            # in the stack and add it to the list of edited data if that is
            # the case and if the edited value is different than the source
            # value.
            for edits in reversed(self._data_edit_stack):
                try:
                    edit = edits[[(edit.index, edit.column) for edit in edits]
                                 .index((last_edit.index, last_edit.column))]
                except ValueError:
                    continue
                else:
                    if edit.edited_value != edit.value:
                        self._edited_dataf.loc[
                            (edit.index, edit.column), 'edited_value'
                            ] = edit.edited_value
                    break

        self._update_visual_data()
        self.sig_data_edited.emit(
            self.has_unsaved_data_edits(), bool(self.data_edit_count()))

    def save_data_edits(self):
        """
        Save all data edits to the database.
        """
        self.sig_data_about_to_be_saved.emit()
        for edits in self._data_edit_stack:
            for edit in edits:
                callback = (self.sig_data_saved.emit
                            if edit == self._data_edit_stack[-1][-1]
                            else None)
                if edit.type() == self.ValueChanged:
                    self.db_connection_manager.set(
                        self.TABLE_DATA_NAME,
                        edit.index, edit.column, edit.edited_value,
                        callback=callback,
                        postpone_exec=True)
        self.db_connection_manager.run_tasks()


class SardesTableModel(SardesTableModelBase):
    """
    An abstract table model to be used in a table view to display the data
    that are saved in the database.

    All table *must* inherit this class and reimplement its interface.

    """
    # A list of tuple that maps the keys of the columns dataframe with their
    # corresponding human readable label to use in the GUI.
    __data_columns_mapper__ = []

    # The label that will be used to reference this table in the GUI.
    TABLE_TITLE = ''

    # A unique ID that will be used to reference this table in the code and
    # in the user configurations.
    TABLE_ID = ''

    # Provide the name of the data and of the required libraries that
    # this table need to fetch from the database.
    TABLE_DATA_NAME = ''
    REQ_LIB_NAMES = []

    def __init__(self, db_connection_manager=None):
        super().__init__(db_connection_manager)

    def create_delegate_for_column(self, view, column):
        """
        Create the item delegate that the view need to use when editing the
        data of this model for the specified column. If None is returned,
        the items of the column will not be editable.
        """
        raise NotImplementedError

    # ---- Visua data
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

    def __init__(self, source_model):
        super().__init__()
        self.setSourceModel(source_model)
        source_model.sig_data_updated.connect(self.invalidate)
        source_model.dataChanged.connect(self.invalidate)

        # Sorting and filtering.
        self._sort_by_columns = []
        self._columns_sort_order = []
        self._filter_by_columns = None
        self._proxy_dataf_index = []

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
        Invalidates the current sorting and filtering.
        """
        self.layoutAboutToBeChanged.emit()

        self._old_persistent_indexes = self.persistentIndexList()
        self._old_persistent_data = [
            (self._proxy_dataf_index[index.row()],
             index.column(),
             index.parent()) for index in self._old_persistent_indexes]

        self._sort()
        self._update_persistent_indexes()

        self.layoutChanged.emit()

    def _update_persistent_indexes(self):
        """
        Update the persistent indexes so that, for instance, the selections
        are preserved correctly after a change.
        """
        new_persistent_indexes = self._old_persistent_indexes.copy()
        for i, (row, column, parent) in enumerate(self._old_persistent_data):
            try:
                new_persistent_indexes[i] = self.index(
                    self._proxy_dataf_index.get_loc(row), column, parent)
            except KeyError:
                new_persistent_indexes[i] = QModelIndex()
        self.changePersistentIndexList(
            self._old_persistent_indexes, new_persistent_indexes)

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

    # ---- Public methods
    def sort(self, column_logical_index, order=Qt.AscendingOrder):
        """
        Override Qt method so that sorting by columns is done with pandas
        instead, which is a lot faster for large datasets.

        https://bugreports.qt.io/browse/QTBUG-45208
        """
        if column_logical_index == -1:
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
            self._sort_by_columns.insert(0, column_logical_index)
            self._columns_sort_order.insert(0, int(order))
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

        source_index_row = self.sourceModel().visual_dataf.index.get_loc(
            self._proxy_dataf_index[proxy_index.row()])
        return self.sourceModel().index(source_index_row, proxy_index.column())

    def mapFromSource(self, source_index):
        """
        Return the model index in the proxy model that corresponds to the
        source_index from the source model.
        """
        if not source_index.isValid() or not len(self._proxy_dataf_index):
            return QModelIndex()

        proxy_index_row = self._proxy_dataf_index.get_loc(
            self.sourceModel().visual_dataf.index[source_index.row()])
        return self.index(proxy_index_row, source_index.column())

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """
        Override Qt method so that the labels of the vertical header always
        start at 1 and are monotically increasing, regardless of the sorting
        and filtering applied to the data.
        """
        if role == Qt.DisplayRole and orientation == Qt.Vertical:
            return section + 1
        else:
            return self.sourceModel().headerData(section, orientation, role)

    def dataf_index_at(self, proxy_index):
        return self.sourceModel().dataf_index_at(
            self.mapToSource(proxy_index))

    def get_dataf_value_at(self, proxy_index):
        return self.sourceModel().get_dataf_value_at(
            self.mapToSource(proxy_index))

    def get_value_at(self, proxy_index):
        return self.sourceModel().get_value_at(
            self.mapToSource(proxy_index))

    def is_data_edited_at(self, proxy_index):
        return self.sourceModel().is_data_edited_at(
            self.mapToSource(proxy_index))

    def get_edited_data_at(self, proxy_index):
        return self.sourceModel().get_edited_data_at(
            self.mapToSource(proxy_index))

    def set_data_edits_at(self, proxy_indexes, edited_values):
        if not isinstance(proxy_indexes, list):
            proxy_indexes = [proxy_indexes, ]
        if not isinstance(edited_values, list):
            edited_values = [edited_values, ]
        return self.sourceModel().set_data_edits_at(
            [self.mapToSource(idx) for idx in proxy_indexes], edited_values)
