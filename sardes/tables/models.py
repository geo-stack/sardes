# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Local imports
from sardes.api.tablemodels import SardesTableModel


class StandardSardesTableModel(SardesTableModel):
    """
    A standard implementation of a Sardes table model that can communicate
    with a database connection manager.
    """
    # =========================================================================
    # ---- API: Mandatory attributes
    # =========================================================================

    # The name that is used to reference in the code and database the data
    # shown in this table.
    __tabledata__: str = None

    # The list of names that is used to reference in the code and database
    # the data that are used as libraries in this table.
    __tablelibs__: list = None

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        # The manager that handle fetching data and pushing data edits to
        # the database.
        self.db_connection_manager = None

    def set_database_connection_manager(self, db_connection_manager):
        """Setup the database connection manager for this table model."""
        self.db_connection_manager = db_connection_manager

    def update_data(self):
        """
        Update this model's data and library.
        """
        if self.db_connection_manager is not None:
            self.db_connection_manager.update_table(self.name())
        else:
            self._raise_db_connmanager_attr_error()
    def _raise_db_connmanager_attr_error(self):
        """
        Raise an attribute error after trying to access an attribute of the
        database connection manager while the later is None.
        """
        raise AttributeError(
            "The database connections manager for the table "
            "model {} is not set.".format(self.name()))

    # ---- SardesTableModel API
    def create_new_row_index(self):
        """
        Extend SardesTableModel method to use the database connection
        manager to generate the new row index.
        """
        if self.db_connection_manager is not None:
            try:
                return self.db_connection_manager.create_new_model_index(
                    self.name())
            except NotImplementedError:
                return super().create_new_row_index()
        else:
            self._raise_db_connmanager_attr_error()

    def check_data_edits(self):
        """
        Check that there is no issues with the data edits of this model.
        """
        raise NotImplementedError

    def save_data_edits(self):
        """
        Save all data edits to the database.
        """
        self.sig_data_about_to_be_saved.emit()

        self.db_connection_manager._data_changed.add(self.__tabledata__)
        self.db_manager.add_task(
            'save_table_edits', None,
            name=self.__tabledata__,
            deleted_rows=self._datat.deleted_rows(),
            added_rows=self._datat.added_rows(),
            edited_values=self._datat.edited_values()
            )
        self.db_manager.run_tasks(callback=self.sig_data_saved.emit)

    def confirm_before_saving_edits(self):
        """
        Return wheter we should ask confirmation to the user before saving
        the data edits to the database.
        """
        if self.db_connection_manager is not None:
            return self.db_connection_manager.confirm_before_saving_edits()
        else:
            self._raise_db_connmanager_attr_error()

    def set_confirm_before_saving_edits(self, x):
        """
        Set wheter we should ask confirmation to the user before saving
        the data edits to the database.
        """
        if self.db_connection_manager is not None:
            self.db_connection_manager.set_confirm_before_saving_edits(x)
        else:
            self._raise_db_connmanager_attr_error()
