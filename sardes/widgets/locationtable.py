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
from qtpy.QtCore import (QAbstractTableModel, QModelIndex,
                         QSortFilterProxyModel, Qt, QVariant, Slot)
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QApplication, QHeaderView, QTableView

# ---- Local imports
from sardes.config.gui import RED, GREEN
from sardes.config.locale import _


class LocationTableModel(QAbstractTableModel):
    """
    An abstract table model to be used in a table view to display the content
    of the databsase locations table.
    """

    COLUMN_LABELS = {'no_well': _('Well ID'),
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
                     'note': _('Note')
                     }
    COLUMNS = list(COLUMN_LABELS.keys())

    def __init__(self):
        super().__init__()
        self.locations = []

    def update_location_table(self, locations):
        """
        Update the content of this table model with the provided list of
        locations.
        """
        self.locations = locations
        self.modelReset.emit()

    def rowCount(self, parent=QModelIndex()):
        """Qt method override. Return the number of row of the table."""
        return len(self.locations)

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
        if role == Qt.DisplayRole:
            column_key = self.COLUMNS[index.column()]
            if column_key == 'is_station_active':
                return ('Yes' if self.locations[index.row()].is_station_active
                        else 'No')
            else:
                return getattr(self.locations[index.row()], column_key)
        elif role == Qt.ForegroundRole:
            column_key = self.COLUMNS[index.column()]
            if column_key == 'is_station_active':
                color = (GREEN if self.locations[index.row()].is_station_active
                         else RED)
                return QColor(color)
            else:
                return QVariant()
        elif role == Qt.ToolTipRole:
            column_key = self.COLUMNS[index.column()]
            if column_key == 'note':
                return getattr(self.locations[index.row()], column_key)
        else:
            return QVariant()


class LocationSortFilterProxyModel(QSortFilterProxyModel):
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

        self.location_table_model = LocationTableModel()
        self.location_proxy_model = LocationSortFilterProxyModel(
            self.location_table_model)

        self.setModel(self.location_proxy_model)
        self.set_database_connection_manager(db_connection_manager)

        self.horizontalHeader().setSectionResizeMode(
            self.location_table_model.columnCount() - 1, QHeaderView.Stretch)

        self.doubleClicked.connect(self._handle_double_clicked)

    @Slot(bool)
    def _trigger_location_table_update(self, connection_state):
        """
        Get the content of locations table from the database and update
        the content of this table view.
        """
        if connection_state:
            self.db_connection_manager.get_observation_wells()
        else:
            self.location_table_model.update_location_table([])

    def set_database_connection_manager(self, db_connection_manager):
        """Setup the database connection manager for this table view."""
        self.db_connection_manager = db_connection_manager
        if db_connection_manager is not None:
            self.db_connection_manager.sig_database_observation_wells.connect(
                self.location_table_model.update_location_table)
            self.db_connection_manager.sig_database_connection_changed.connect(
                self._trigger_location_table_update)

    def _handle_double_clicked(self, proxy_index):
        model_index = self.location_proxy_model.mapToSource(proxy_index)
        print(self.location_table_model.locations[model_index.row()])


if __name__ == '__main__':
    from sardes.widgets.databaseconnector import DatabaseConnectionWidget
    from sardes.database.manager import DatabaseConnectionManager
    app = QApplication(sys.argv)

    manager = DatabaseConnectionManager()

    connection_widget = DatabaseConnectionWidget(manager)
    connection_widget.show()

    table_view = ObservationWellTableView(manager)
    table_view.show()

    connection_widget.connect()
    sys.exit(app.exec_())
