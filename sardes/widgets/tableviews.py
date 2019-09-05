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


class SardesTableModel(QAbstractTableModel):
    """
    An abstract table model to be used in a table view to display the list of
    observation wells that are saved in the database.
    """
    # A list of tuple that maps the keys of the columns dataframe with their
    # corresponding human readable label to use in the GUI.
    __data_columns_mapper__ = []

    # The method to call on the database connection manager to retrieve the
    # data for this model.
    __get_data_method__ = None

    def __init__(self, db_connection_manager=None):
        super().__init__()
        self.__data_columns_mapper__ = OrderedDict(
            self.__data_columns_mapper__)
        self.dataf = pd.DataFrame([])
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
        return list(self.__data_columns_mapper__.keys())

    def columnCount(self, parent=QModelIndex()):
        """Qt method override. Return the number of column of the table."""
        return len(self.columns)

    # ---- Horizontal Headers
    @property
    def horizontal_header_labels(self):
        return list(self.__data_columns_mapper__.values())

    def get_horizontal_header_label_at(self, column_or_index):
        return self.__data_columns_mapper__[
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
            self.db_connection_manager, self.__get_data_method__)
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
                value = self.dataf.iloc[row, column]
                value = '' if pd.isna(value) else value
            return str(value)
        elif role == Qt.ForegroundRole:
            return QVariant()
        elif role == Qt.ToolTipRole:
            return (QVariant() if column is None
                    else self.dataf.iloc[row, column])
        else:
            return QVariant()


class SardesSortFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, source_model):
        super().__init__()
        self.setSourceModel(source_model)


class SardesTableView(QTableView):
    """
    A single table view that displays the list of observation wells
    that are saved in the database.
    """

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(True)
        self.setCornerButtonEnabled(False)
        self.horizontalHeader().setSectionsMovable(True)

        self.set_table_model(model)
        self._columns_options_button = None
        self._toggle_column_visibility_actions = []

    def set_table_model(self, source_model):
        """Setup the data model for this table view."""
        self.source_model = source_model
        self.proxy_model = SardesSortFilterProxyModel(source_model)
        self.setModel(self.proxy_model)

    # ---- Utilities
    def get_selected_rows_data(self):
        """
        Return the data relative to the currently selected rows in this table.
        """
        proxy_indexes = self.selectionModel().selectedIndexes()
        rows = [self.proxy_model.mapToSource(i).row() for i in proxy_indexes]
        return self.source_model.dataf.iloc[rows]

    def get_selected_row_data(self):
        """
        Return the data relative to the currently selected row in this table.
        If more than one row is selected, the data from the first row of the
        selection is returned.
        """
        selected_data = self.get_selected_rows_data()
        if len(selected_data) > 0:
            row_data = selected_data.iloc[0]
        else:
            row_data = None
        return row_data

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


if __name__ == '__main__':
    from sardes.database.database_manager import DatabaseConnectionManager
    app = QApplication(sys.argv)

    manager = DatabaseConnectionManager()
    table_view = SardesTableView(manager)
    table_view.show()
    manager.connect_to_db('debug')

    sys.exit(app.exec_())