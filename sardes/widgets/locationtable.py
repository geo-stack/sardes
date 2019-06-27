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


class LocationTableModel(QAbstractTableModel):
    """
    An abstract table model to be used in a table view to display the content
    of the databsase locations table.
    """

    COLUMNS = ['no_piezometre', 'nom_communn', 'municipalite',
               'aquifere', 'nappe', 'code_aqui', 'zone_rechar',
               'influences', 'latitude_8', 'longitude', 'station_active',
               'remarque']
    COLUMN_LABELS = {'no_piezometre': 'Piezometer ID',
                     'nom_communn': 'Common Name',
                     'municipalite': 'Municipality',
                     'aquifere': 'Aquifer',
                     'nappe': 'Confinement',
                     'code_aqui': 'Aquifer Code',
                     'zone_rechar': 'Recharge Zone',
                     'influences': 'Influenced',
                     'latitude_8': 'Latitude',
                     'longitude': 'Longitude',
                     'station_active': 'Active',
                     'remarque': 'Note'
                     }

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
            if column_key == 'station_active':
                return ('Yes' if self.locations[index.row()].station_active
                        else 'No')
            else:
                return getattr(self.locations[index.row()], column_key)
        elif role == Qt.ForegroundRole:
            column_key = self.COLUMNS[index.column()]
            if column_key == 'station_active':
                color = (GREEN if self.locations[index.row()].station_active
                         else RED)
                return QColor(color)
            else:
                return QVariant()
        elif role == Qt.ToolTipRole:
            column_key = self.COLUMNS[index.column()]
            if column_key == 'remarque':
                return getattr(self.locations[index.row()], column_key)
        else:
            return QVariant()


class LocationSortFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, source_model, date_span=None):
        super().__init__()
        self.setSourceModel(source_model)


class LocationTableView(QTableView):
    """
    A single table view that displays the content of the databsase locations
    table.
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

    @Slot(bool)
    def _trigger_location_table_update(self, connection_state):
        """
        Get the content of locations table from the database and update
        the content of this table view.
        """
        if connection_state:
            self.db_connection_manager.get_locations()
        else:
            self.location_table_model.update_location_table([])

    def set_database_connection_manager(self, db_connection_manager):
        """Setup the database connection manager for this table view."""
        self.db_connection_manager = db_connection_manager
        if db_connection_manager is not None:
            self.db_connection_manager.sig_database_locations.connect(
                self.location_table_model.update_location_table)
            self.db_connection_manager.sig_database_connection_changed.connect(
                self._trigger_location_table_update)


if __name__ == '__main__':
    from sardes.widgets.databaseconnector import DatabaseConnectionWidget
    from sardes.database.manager import DatabaseConnectionManager
    app = QApplication(sys.argv)

    manager = DatabaseConnectionManager()

    connection_widget = DatabaseConnectionWidget(manager)
    connection_widget.show()

    table_view = LocationTableView(manager)
    table_view.show()

    connection_widget.connect()
    sys.exit(app.exec_())
