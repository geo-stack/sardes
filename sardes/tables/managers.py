# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Third party imports
from qtpy.QtCore import QObject, Signal


class SardesTableModelsManager(QObject):
    """
    A manager to handle data updating and saving of Sardes table models.
    """
    sig_models_data_changed = Signal()

    def __init__(self, db_manager):
        super().__init__()
        self._table_models = {}
        self._queued_model_updates = {}
        self._running_model_updates = {}
        # _queued_model_updates contains the lists of data and library names
        # that need to be updated for each table registered to this manager
        # when the update_table is called.
        #
        # _running_model_updates contains the lists of data and library names
        # that are currently being updated after the update_table was
        # called.

        # Setup the database manager.
        self.db_manager = db_manager
        db_manager.sig_database_connection_changed.connect(
            self._handle_db_connection_changed)
        db_manager.sig_database_data_changed.connect(
            self._handle_db_data_changed)
        self.sig_models_data_changed.connect(
            self.db_manager.sig_models_data_changed.emit)

    # ---- Public API
    def table_models(self):
        """Return the list of table models registered to this manager."""
        return list(self._table_models.values())

    def register_table_model(self, table_model):
        """
        Register a new sardes table model to the manager.
        """
        table_name = table_model.name()
        self._table_models[table_name] = table_model
        self._queued_model_updates[table_name] = (
            [table_model.__tabledata__] + table_model.__tablelibs__)
        self._running_model_updates[table_name] = []

    def update_table_model(self, table_name):
        """
        Update the given sardes table model.
        """
        if table_name not in self._table_models:
            raise Warning("Warning: Table model '{}' is not registered."
                          .format(table_name))
            return

        if len(self._queued_model_updates[table_name]):
            self._table_models[table_name].sig_data_about_to_be_updated.emit()
            for name in self._queued_model_updates[table_name]:
                self._running_model_updates[table_name].append(name)
                self.db_manager.get(
                    name,
                    callback=lambda dataf, name=name:
                        self._set_model_data_or_lib(dataf, name, table_name),
                    postpone_exec=True)
            self._queued_model_updates[table_name] = []
            self.db_manager.run_tasks()

    # ---- Private API
    def _set_model_data_or_lib(self, dataf, data_name, table_name):
        """
        Set the data or library of the given table model.
        """
        table_model = self._table_models[table_name]
        if data_name == table_model.__tabledata__:
            # Update the table model data.
            table_model.set_model_data(dataf)
        elif data_name in table_model.__tablelibs__:
            # Update the table model library.
            table_model.set_model_library(dataf, data_name)

        self._running_model_updates[table_name].remove(data_name)
        if not len(self._running_model_updates[table_name]):
            table_model.sig_data_updated.emit()

    def _handle_db_data_changed(self, data_changed):
        """
        Handle when changes are made to the database.

        Note that changes made to the database outside of Sardes are not
        taken into account here.
        """
        for table_name, table_model in self._table_models.items():
            data_libs_names = (
                [table_model.__tabledata__] + table_model.__tablelibs__)
            self._queued_model_updates[table_name].extend(
                [name for name in data_changed if name in data_libs_names])
            self._queued_model_updates[table_name] = list(set(
                self._queued_model_updates[table_name]))
        self.sig_models_data_changed.emit()

    def _handle_db_connection_changed(self, is_connected):
        """
        Handle when the connection to the database changes.
        """
        if is_connected:
            for table_name, table_model in self._table_models.items():
                self._queued_model_updates[table_name] = (
                    [table_model.__tabledata__] + table_model.__tablelibs__)
        else:
            for table_name, table_model in self._table_models.items():
                self._queued_model_updates[table_name] = []
                table_model.clear_data()
        self.sig_models_data_changed.emit()
