# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Standard imports
import sys
from collections import OrderedDict

# ---- Third party imports
import pandas as pd
from qtpy.QtCore import (QAbstractTableModel, QModelIndex,
                         QSortFilterProxyModel, Qt, QVariant, Slot)
from qtpy.QtWidgets import QApplication, QMenu, QTableView

# ---- Local imports
from sardes.config.locale import _
from sardes.config.gui import get_iconsize
from sardes.utils.qthelpers import (
    create_action, create_toolbutton, qbytearray_to_hexstate,
    hexstate_to_qbytearray)


class NoDataEdit(object):
    """
    A class to indicate that no edit have been done to the data since last
    save.
    """

    def __init__(self, model_index):
        super() .__init__()
        self.model_index = model_index


# =============================================================================
# ---- Table Model
# =============================================================================
class SardesTableModel(QAbstractTableModel):
    """
    An abstract table model to be used in a table view to display the list of
    observation wells that are saved in the database.
    """
    sig_data_edited = Signal(bool)

    def __init__(self, data_columns_mapper, get_data_method,
                 db_connection_manager=None):
        super().__init__()
        self._data_columns_mapper = OrderedDict(data_columns_mapper)
        self._get_data_method = get_data_method
        self._is_column_editable = {}

        # A pandas dataframe containing the data that are shown in the
        # database.
        self.dataf = pd.DataFrame([])

        # A dictionary containing the edits made by the user to the
        # content of this table's model data.
        self._dataf_edits = {}

        self.set_database_connection_manager(db_connection_manager)

    def set_database_connection_manager(self, db_connection_manager):
        """Setup the database connection manager for this table model."""
        self.db_connection_manager = db_connection_manager
        if db_connection_manager is not None:
            self.db_connection_manager.sig_database_connection_changed.connect(
                self._trigger_data_update)

    # ---- Columns
    @property
    def columns(self):
        """
        Return the list of keys used to reference the columns in this
        model's data.
        """
        return list(self._data_columns_mapper.keys())

    def columnCount(self, parent=QModelIndex()):
        """Qt method override. Return the number of column of the table."""
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

    def headerData(self, section, orientation, role):
        """Qt method override."""
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.get_horizontal_header_label_at(section)
        if role == Qt.DisplayRole and orientation == Qt.Vertical:
            return section
        else:
            return QVariant()

    # ---- Table data
    def _update_data(self, dataf):
        """
        Update the content of this table model with the data
        contained in dataf.

        Parameters
        ----------
        dataf: :class:`pd.DataFrame`
            A pandas dataframe containing the data of this table model. The
            column labels of the dataframe must match the values that are
            mapped in HORIZONTAL_HEADER_LABELS.
        """
        self.dataf = dataf
        self.modelReset.emit()

    @Slot(bool)
    def _trigger_data_update(self, connection_state):
        """
        Get the list of observation wells that are saved in the database and
        update the content of this table view.
        """
        get_data_method = getattr(
            self.db_connection_manager, self._get_data_method)
        get_data_method(callback=self._update_data)

    def rowCount(self, parent=QModelIndex()):
        """Qt method override. Return the number of row of the table."""
        return len(self.dataf)

    def data(self, index, role=Qt.DisplayRole):
        """Qt method override."""
        column_key = self.columns[index.column()]
        row = index.row()
        try:
            column = self.dataf.columns.get_loc(column_key)
        except KeyError:
            column = None

        if role == Qt.DisplayRole:
            if column is None:
                value = ''
            else:
                value = self.get_data_edits_at(index)
                if isinstance(value, NoDataEdit):
                    value = self.dataf.iloc[row, column]
                value = '' if (pd.isna(value) or value is None) else value
            if pd.api.types.is_bool(value):
                value = _('Yes') if value else _('No')
            return str(value)
        elif role == Qt.ForegroundRole:
            return QVariant()
        elif role == Qt.BackgroundRole:
            return (QVariant() if
                    isinstance(self.get_data_edits_at(index), NoDataEdit)
                    else QColor('#CCFF99'))
        elif role == Qt.ToolTipRole:
            return (QVariant() if column is None
                    else self.dataf.iloc[row, column])
        else:
            return QVariant()

    def flags(self, model_index):
        """Qt method override."""
        if self.is_item_editable(model_index):
            return Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable
        else:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def get_data_at(self, model_index, ignore_edits=False):
        """
        Return the value of the model's data at the specified model index.
        """
        # We check first if the data was edited by the user if 'ignore_edits'
        # is True.
        value = (NoDataEdit(model_index) if ignore_edits else
                 self.get_data_edits_at(model_index))
        if isinstance(value, NoDataEdit):
            # This means that the value was not edited by the user, so we
            # fetch the value directly from the model's data.
            column_key = self.columns[model_index.column()]
            try:
                dataf_column = self.dataf.columns.get_loc(column_key)
            except KeyError:
                value = None
            else:
                dataf_row = model_index.row()
                value = self.dataf.iloc[dataf_row, dataf_column]
        return value

    # ---- Data edits
    def is_item_editable(self, model_index):
        """
        Return whether the item at the specified model index is editable.
        """
        return self._is_column_editable.get(
            self.columns[model_index.column()], False)

    def set_column_editable(self, column, value):
        """
        Set whether the items for the specified column are editable.
        """
        self._is_column_editable[column] = value

    def has_unsaved_data_edits(self):
        """
        Return whether edits were made to the table since last save.
        """
        return len(self._dataf_edits) > 0

    def has_unsaved_data_edits_at(self, model_index):
        """
        Return whether edits were made at the specified model index
        since last save.
        """
        dataf_index = self.dataf.index[model_index.row()]
        dataf_column = self.columns[model_index.column()]
        try:
            self._dataf_edits[dataf_index][dataf_column]
        except KeyError:
            return False
        else:
            return True

    def cancel_all_data_edits(self):
        """
        Cancel all the edits that were made to the table data since last save.
        """
        self._dataf_edits = {}
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.rowCount() - 1, self.columnCount() - 1))
        self.sig_data_edited.emit(False)

    def cancel_data_edits_at(self, model_indexes):
        """
        Cancel the edits, if any, that were made at the specified model indexes
        since last save.
        """
        if not isinstance(model_indexes, [list, tuple]):
            model_indexes = [model_indexes, ]
        for model_index in model_indexes:
            dataf_index = self.dataf.index[model_index.row()]
            dataf_column = self.columns[model_index.column()]
            try:
                del self._dataf_edits[dataf_index][dataf_column]
                if len(self._dataf_edits[dataf_index]) == 0:
                    del self._dataf_edits[dataf_index]
            except KeyError:
                pass
            else:
                self.dataChanged.emit(model_index, model_index)
                self.sig_data_edited.emit(self.has_unsaved_data_edits())


    def get_data_edits_at(self, model_index):
        """
        Return the edited value, if any, that was made at the specified
        model index since last save.
        """
        dataf_index = self.dataf.index[model_index.row()]
        dataf_column = self.columns[model_index.column()]
        try:
            return self._dataf_edits[dataf_index][dataf_column]
        except KeyError:
            return NoDataEdit(model_index)

    def set_data_edits_at(self, model_index, new_value):
        """
        Store the value that was edited at the specified model index.
        If the edited value corresponds to the value stored in the model's
        unsaved data, then any edited value stored at that model index is
        discarted. A signal is also emitted at the end of this method to
        indicate that the data were edited so that the GUI can be updated
        accordingly.
        """
        model_value = self.get_data_at(model_index, ignore_edits=True)
        if model_value == new_value:
            # We remove this from the list of unsaved data changes since the
            # new value is the same as that of the database.
            self.cancel_data_edits_at(model_index)
        else:
            # We store the edited value until it is commited and saved to the
            # database.
            dataf_column = self.columns[model_index.column()]
            dataf_index = self.dataf.index[model_index.row()]
            try:
                self._dataf_edits[dataf_index].update({
                    dataf_column: new_value})
            except KeyError:
                self._dataf_edits[dataf_index] = {
                    dataf_column: new_value}
        self.sig_data_edited.emit(self.has_unsaved_data_edits())


class SardesSortFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, source_model):
        super().__init__()
        self.setSourceModel(source_model)

    def get_data_at(self, proxy_index, ignore_edits=False):
        """
        Return the value of the model's data at the specified model index.
        """
        return self.sourceModel().get_data_at(self.mapToSource(proxy_index))

    # ---- Data edits
    def is_item_editable(self, proxy_index):
        """
        Return whether the item at the specified model index is editable.
        """
        return self.sourceModel().is_item_editable(
            self.mapToSource(proxy_index))

    def cancel_data_edits_at(self, proxy_indexes):
        """
        Cancel the edits that were made at the specified proxy model indexes
        since last save if any.
        """
        self.sourceModel().cancel_data_edits_at(
            self.mapToSource(proxy_indexes))

    def set_data_edits_at(self, proxy_index, value):
        """
        Store the value that was edited at the specified proxy model index.
        """
        self.sourceModel().set_data_edits_at(
            self.mapToSource(proxy_index), value)


class SardesTableViewBase(QTableView):
    """
    Basic functionality for Sardes table views.

    WARNING: Don't override any methods or attributes present here.
    """
    sig_data_edited = Signal(bool)

    def __init__(self, db_connection_manager, parent=None):
        super().__init__(parent)
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(True)
        self.setCornerButtonEnabled(False)
        self.horizontalHeader().setSectionsMovable(True)
        self.setMouseTracking(True)

        self._setup_table_model(db_connection_manager)
        self._setup_item_delegates()

        # Toolbuttons.
        self._columns_options_button = None
        self._toggle_column_visibility_actions = []

        self._edit_selection_button = None
        self._cancel_edits_button = None
        self._commit_edits_button = None

    def _setup_table_model(self, db_connection_manager):
        """
        Setup the data model for this table view.
        """
        self.source_model = SardesTableModel(
            self.DATA_COLUMNS_MAPPER,
            self.GET_DATA_METHOD,
            db_connection_manager)
        self.source_model.sig_data_edited.connect(self.sig_data_edited.emit)
        self.proxy_model = SardesSortFilterProxyModel(self.source_model)
        self.setModel(self.proxy_model)

    def _setup_item_delegates(self):
        """
        Setup the item delegates for each column of this table view.
        """
        for i, column in enumerate(self.source_model.columns):
            item_delegate = self.create_delegate_for_column(column)
            self.setItemDelegateForColumn(i, item_delegate)
            self.source_model.set_column_editable(
                column, item_delegate is not None)

    # ---- Utilities
    def get_selected_rows_data(self):
        """
        Return the data relative to the currently selected rows in this table.
        """
        proxy_indexes = self.selectionModel().selectedIndexes()
        rows = sorted(list(set(
            [(self.proxy_model.mapToSource(i).row()) for i in proxy_indexes]
            )))
        return self.source_model.dataf.iloc[rows]

    def get_selected_row_data(self):
        """
        Return the data relative to the currently selected row in this table.
        If more than one row is selected, the data from the first row of the
        selection is returned.
        """
        selected_data = self.get_selected_rows_data()
        if len(selected_data) > 0:
            row_data = selected_data.iloc[[0]]
        else:
            row_data = None
        return row_data

    def row_count(self):
        """Return this table number of visible row."""
        return self.proxy_model.rowCount()

    def selected_row_count(self):
        """
        Return the number of rows of this table that have at least one
        selected items.
        """
        return len(self.get_selected_rows_data())

    # ---- Column options
    def column_count(self):
        """Return this table number of visible and hidden columns."""
        return self.horizontalHeader().count()

    def hidden_column_count(self):
        """Return this table number of hidden columns."""
        return self.horizontalHeader().hiddenSectionCount()

    def visible_column_count(self):
        """Return this table number of visible columns."""
        return self.column_count() - self.hidden_column_count()

    def get_horiz_header_state(self):
        """
        Return the current state of this table horizontal header.
        """
        return qbytearray_to_hexstate(self.horizontalHeader().saveState())

    def restore_horiz_header_state(self, hexstate):
        """
        Restore the state of this table horizontal header from hexstate.
        """
        if hexstate is not None:
            self.horizontalHeader().restoreState(
                hexstate_to_qbytearray(hexstate))

    def show_all_available_columns(self):
        """
        Set the visibility of all available columns of this table to true.
        """
        for action in self._toggle_column_visibility_actions:
            action.setChecked(True)

    def restore_horiz_header_to_defaults(self):
        """
        Restore the visibility and order of this table columns to the
        default values.
        """
        self.show_all_available_columns()
        for logical_index, column in enumerate(self.source_model.columns):
            self.horizontalHeader().moveSection(
                self.horizontalHeader().visualIndex(logical_index),
                logical_index)
        self.resizeColumnsToContents()

    def get_column_options_button(self):
        """
        Return a toolbutton with a menu that contains actions to toggle the
        visibility of the available columns of this table.
        """
        if self._columns_options_button is None:
            self._create_columns_options_button()
        return self._columns_options_button

    def _create_columns_options_button(self):
        """
        Create and return a toolbutton with a menu that contains actions
        to toggle the visibility of the available columns of this table.
        """
        # Create the column options button.
        self._columns_options_button = create_toolbutton(
            self,
            icon='table_columns',
            text=_("Column options"),
            tip=_("Open a menu to select the columns to "
                  "display in this table."),
            iconsize=get_iconsize()
            )
        self._columns_options_button.setPopupMode(
            self._columns_options_button.InstantPopup)

        # Create the column options menu.
        columns_options_menu = QMenu()
        self._columns_options_button.setMenu(columns_options_menu)

        # Add a show all column and restore to defaults action.
        columns_options_menu.addAction(create_action(
            self, _('Restore to defaults'),
            triggered=self.restore_horiz_header_to_defaults))
        columns_options_menu.addAction(create_action(
            self, _('Show all'),
            triggered=self.show_all_available_columns))
        columns_options_menu.addSeparator()

        # Add an action to toggle the visibility for each available
        # column of this table.
        self._toggle_column_visibility_actions = []
        for i, label in enumerate(self.source_model.horizontal_header_labels):
            action = create_action(
                self, label,
                toggled=(lambda toggle,
                         logical_index=i:
                         self.horizontalHeader().setSectionHidden(
                             logical_index, not toggle)
                         ))
            self._toggle_column_visibility_actions.append(action)
            columns_options_menu.addAction(action)
            action.setChecked(not self.horizontalHeader().isSectionHidden(i))

    # ---- Data edits
    @property
    def edit_selection_button(self):
        """
        Return a toolbutton that will turn on edit mode for the first editable
        cell selected in this table view when triggered.
        """
        if self._edit_selection_button is None:
            self._edit_selection_button = create_toolbutton(
                self,
                icon='edit_database_item',
                text=_("Edit observation well"),
                tip=_('Edit the currently selected observation well.'),
                shortcut='Ctrl+E',
                triggered=self._edit_selection,
                iconsize=get_iconsize()
                )
        return self._commit_changes_button

    def _edit_selection(self):
        """
        Turn on edit mode for the first editable cell selected in this table.
        """
        for model_index in self.selectionModel().selectedIndexes():
            if self.model().is_item_editable(model_index):
                break
        self._edit_data_at(model_index)

    def _edit_data_at(self, model_index):
        """
        Turn on edit mode for the cell at the specified model index.
        """
        if (model_index is not None and
                self.model().is_item_editable(model_index)):
            self.edit(model_index)

    @property
    def commit_edits_button(self):
        """
        Return a toolbutton that save the edits made to the data of the
        table when triggered.
        """
        if self._commit_changes_button is None:
            self._commit_changes_button = create_toolbutton(
                self,
                icon='commit_changes',
                text=_("Edit observation well"),
                tip=_('Edit the currently selected observation well.'),
                triggered=lambda: self._save_data_edits(force=False),
                iconsize=get_iconsize()
                )
            self._commit_changes_button.setEnabled(False)
            self.sig_data_edited.connect(
                self._commit_changes_button.setEnabled)
        return self._commit_changes_button

    def _save_data_edits(self, force=True):
        """
        Save the data edits to the database. If 'force' is 'False', a message
        is first shown before proceeding.
        """
        if force is False:
            reply = QMessageBox.warning(
                self, _('Save changes'),
                _("This will permanently save the changes made in this "
                  "table in the database.<br><br>"
                  "This action <b>cannot</b> be undone."),
                buttons=QMessageBox.Ok | QMessageBox.Cancel
                )
            if reply == QMessageBox.Cancel:
                return
        self.source_model.save_data_edits()

    @property
    def cancel_edits_button(self):
        """
        Return a toolbutton that cancel all the edits that were made to
        the data of the table since last save when triggered.
        """
        if self._cancel_changes_button is None:
            self._cancel_changes_button = create_toolbutton(
                self,
                icon='cancel_changes',
                text=_("Edit observation well"),
                tip=_('Edit the currently selected observation well.'),
                triggered=self.source_model.cancel_all_data_edits,
                iconsize=get_iconsize()
                )
            self._cancel_edits_button.setEnabled(False)
            self.sig_data_edited.connect(self._cancel_edits_button.setEnabled)
        return self._cancel_edits_button


class SardesTableView(SardesTableViewBase):
    """
    Sardes table view class to display and edit the data that are
    saved in the database.

    All table *must* inherit this class and reimplement its interface.
    """
    # A list of tuple that maps the keys of the columns dataframe with their
    # corresponding human readable label to use in the GUI.
    DATA_COLUMNS_MAPPER = []

    # The name of the method that the database connection manager need to call
    # to retrieve the data from the database for this table view.
    GET_DATA_METHOD = None

    def __init__(self, db_connection_manager=None, parent=None):
        super().__init__(db_connection_manager, parent)

    def create_delegate_for_column(self, column):
        """
        Create the item delegate that this model's table view need to use
        for the specified column. If None is returned, the items of the
        column will not be editable.

        All table model *must* reimplement this method to return the
        appropriate delegate to be used for each columns of its
        corresponding table.
        """
        raise NotImplementedError


if __name__ == '__main__':
    from sardes.database.database_manager import DatabaseConnectionManager
    app = QApplication(sys.argv)

    manager = DatabaseConnectionManager()
    table_view = SardesTableView(manager)
    table_view.show()
    manager.connect_to_db('debug')

    sys.exit(app.exec_())
