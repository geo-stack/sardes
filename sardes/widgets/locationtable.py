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

# ---- Third party imports
import pandas as pd
from qtpy.QtCore import (QAbstractTableModel, QModelIndex,
                         QSortFilterProxyModel, Qt, QVariant, Slot)
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QApplication, QHeaderView, QMenu, QTableView

# ---- Local imports
from sardes.config.gui import RED, GREEN
from sardes.config.locale import _
from sardes.config.gui import get_iconsize
from sardes.utils.qthelpers import (
    create_action, create_toolbutton, qbytearray_to_hexstate,
    hexstate_to_qbytearray)


class ObsWellTableModel(QAbstractTableModel):
    """
    An abstract table model to be used in a table view to display the list of
    observation wells that are saved in the database.
    """

    COLUMN_LABELS = {'obs_well_id': _('Well ID'),
                     'common_name': _('Common Name'),
                     'municipality': _('Municipality'),
                     'aquifer_type': _('Aquifer'),
                     'aquifer_code': _('Aquifer Code'),
                     'confinement': _('Confinement'),
                     'in_recharge_zone': _('Recharge Zone'),
                     'is_influenced': _('Influenced'),
                     'latitude': _('Latitude'),
                     'longitude': _('Longitude'),
                     'is_station_active': _('Active'),
                     'obs_well_notes': _('Note')
                     }
    COLUMNS = list(COLUMN_LABELS.keys())

    def __init__(self):
        super().__init__()
        self.obs_wells = []

    def update_obs_well_table(self, obs_wells):
        """
        Update the content of this table model with the provided list of
        observation wells.
        """
        self.obs_wells = obs_wells
        self.modelReset.emit()

    def rowCount(self, parent=QModelIndex()):
        """Qt method override. Return the number of row of the table."""
        return len(self.obs_wells)

    def columnCount(self, parent=QModelIndex()):
        """Qt method override. Return the number of column of the table."""
        return len(self.COLUMNS)

    def headerData(self, section, orientation, role):
        """Qt method override."""
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.COLUMN_LABELS[self.COLUMNS[section]]
        if role == Qt.DisplayRole and orientation == Qt.Vertical:
            return section
        else:
            return QVariant()

    def data(self, index, role=Qt.DisplayRole):
        """Qt method override."""
        column_key = self.COLUMNS[index.column()]
        row = index.row()
        try:
            column = self.obs_wells.columns.get_loc(column_key)
        except ValueError:
            column = None

        if role == Qt.DisplayRole:
            if column is None:
                value = ''
            else:
                value = self.obs_wells.iloc[row, column]
                value = '' if pd.isna(value) else value
            return str(value)
        elif role == Qt.ForegroundRole:
            if column_key == 'is_station_active' and column is not None:
                color = (GREEN if
                         self.obs_wells.iloc[row, column] == 'True'
                         else RED)
                return QColor(color)
            else:
                return QVariant()
        elif role == Qt.ToolTipRole:
            return (QVariant() if column is None
                    else self.obs_wells.iloc[row, column])
        else:
            return QVariant()


class ObsWellSortFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, source_model, date_span=None):
        super().__init__()
        self.setSourceModel(source_model)


class ObservationWellTableView(QTableView):
    """
    A single table view that displays the list of observation wells
    that are saved in the database.
    """

    def __init__(self, db_connection_manager=None, parent=None):
        super().__init__(parent)
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(True)
        self.setCornerButtonEnabled(False)

        self.obs_well_table_model = ObsWellTableModel()
        self.obs_well_proxy_model = ObsWellSortFilterProxyModel(
            self.obs_well_table_model)

        self.setModel(self.obs_well_proxy_model)
        self.set_database_connection_manager(db_connection_manager)

        self.horizontalHeader().setSectionResizeMode(
            self.obs_well_table_model.columnCount() - 1, QHeaderView.Stretch)
        self.horizontalHeader().setSectionsMovable(True)

        self._columns_options_button = None
        self._toggle_column_visibility_actions = []

    @Slot(bool)
    def _trigger_obs_well_table_update(self, connection_state):
        """
        Get the list of observation wells that are saved in the database and
        update the content of this table view.
        """
        self.db_connection_manager.get_observation_wells(
            callback=self.obs_well_table_model.update_obs_well_table)

    def set_database_connection_manager(self, db_connection_manager):
        """Setup the database connection manager for this table view."""
        self.db_connection_manager = db_connection_manager
        if db_connection_manager is not None:
            self.db_connection_manager.sig_database_connection_changed.connect(
                self._trigger_obs_well_table_update)

    # ---- Column options
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
        for logical_index, column in enumerate(
                self.obs_well_table_model.COLUMNS):
            self.horizontalHeader().moveSection(
                self.horizontalHeader().visualIndex(logical_index),
                logical_index)

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
            tip=_("Open this table's column options menu."),
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
        columns = self.obs_well_table_model.COLUMNS
        columns_labels = self.obs_well_table_model.COLUMN_LABELS
        self._toggle_column_visibility_actions = []
        for i, column in enumerate(columns):
            action = create_action(
                self, columns_labels[column],
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
    table_view = ObservationWellTableView(manager)
    table_view.show()
    manager.connect_to_db('debug')

    sys.exit(app.exec_())
