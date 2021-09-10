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
        self._models_req_data = {}
        self._queued_model_updates = {}
        self._running_model_updates = {}
        # _queued_model_updates contains the lists of data and library names
        # that need to be updated for each table registered to this manager
        # when the update_model is called.
        #
        # _running_model_updates contains the lists of data and library names
        # that are currently being updated after the update_model was
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
    def register_model(self, table_model, data_name, lib_names=None):
        """
        Register a new sardes table model to the manager.
        """
        lib_names = lib_names or []
        table_id = table_model.name()
        self._table_models[table_id] = table_model
        self._models_req_data[table_id] = [data_name] + lib_names
        self._queued_model_updates[table_id] = [data_name] + lib_names
        self._running_model_updates[table_id] = []

    def update_model(self, table_name):
        """
        Update the given sardes table.
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

    def save_table_edits(self, table_id):
        """
        Save all data edits to the database.
        """
        table_model = self._table_models[table_id]
        table_model.sig_data_about_to_be_saved.emit()
        table_name = self._models_req_data[table_id][0]

        deleted_rows = table_model._datat.deleted_rows()
        added_rows = table_model._datat.added_rows()
        edited_values = table_model._datat.edited_values()

        self.db_manager._data_changed.add(table_name)
        self.db_manager.add_task(
            'save_table_edits', None,
            table_name, deleted_rows, added_rows, edited_values,
            )

        self.db_manager.run_tasks(callback=table_model.sig_data_saved.emit)

    def check_table_edits(self, table_id, callback):
        """
        Check that there is no issues with the data edits made on the
        table model related to table_id.
        """
        table_model = self._table_models[table_id]
        table_name = self._models_req_data[table_id][0]
        table_columns = table_model.columns()

        deleted_rows = table_model._datat.deleted_rows()
        added_rows = table_model._datat.added_rows()
        edited_values = table_model._datat.edited_values()

        self.db_manager.add_task(
            'check_table_edits', callback,
            table_name, table_columns, deleted_rows, added_rows, edited_values
            )
        self.db_manager.run_tasks()

    # ---- Private API
    def _set_model_data_or_lib(self, dataf, name, table_id):
        """
        Set the data or library of the given table model.
        """
        if name == self._models_req_data[table_id][0]:
            # Update the table model data.
            self._table_models[table_id].set_model_data(dataf)
        elif name in self._models_req_data[table_id][1:]:
            # Update the table model library.
            self._table_models[table_id].set_model_library(dataf, name)

        self._running_model_updates[table_id].remove(name)
        if not len(self._running_model_updates[table_id]):
            self._table_models[table_id].sig_data_updated.emit()

    def _handle_db_data_changed(self):
        """
        Handle when changes are made to the database.

        Note that changes made to the database outside of Sardes are not
        taken into account here.
        """
        data_changed = list(self.db_manager._data_changed)
        for table_id, table in self._table_models.items():
            req_data_names = self._models_req_data[table_id]
            self._queued_model_updates[table_id].extend(
                [name for name in data_changed if name in req_data_names])
            self._queued_model_updates[table_id] = list(set(
                self._queued_model_updates[table_id]))
        self.sig_models_data_changed.emit()

    def _handle_db_connection_changed(self, is_connected):
        """
        Handle when the connection to the database changes.
        """
        if is_connected:
            for table_id, table in self._table_models.items():
                self._queued_model_updates[table_id] = (
                    self._models_req_data[table_id].copy())
        else:
            for table_id, table in self._table_models.items():
                self._queued_model_updates[table_id] = []
                table.clear_data()
        self.sig_models_data_changed.emit()
