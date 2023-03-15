# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sardes.tables.managers import SardesTableModelsManager
    


import pandas as pd

# ---- Local imports
from sardes.api.tablemodels import SardesTableModel
from sardes.tables.errors import (
    NotNullTableEditError, UniqueTableEditError, ForeignTableEditError)


class StandardSardesTableModel(SardesTableModel):
    """
    A standard implementation of a Sardes table model that can communicate
    with a database connection manager.
    """
    # =========================================================================
    # ---- API: Mandatory attributes
    # =========================================================================

    # The name that is used to reference in the database connection manager
    # the data shown in this table.
    __dataname__: str = None

    # The list of names that is used to reference in the database connection
    # manager the data that are used as libraries in this table.
    __libnames__: list = None

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        # The manager that handle fetching data and pushing data edits to
        # the database and that link all the Sardes tables together.
        self.table_models_manager = None

    @property
    def db_connection_manager(self):
        """Return Sardes database connection manager."""
        return self.table_models_manager.db_manager

    def set_table_models_manager(
            self, table_models_manager: SardesTableModelsManager):
        """Set the table models manager."""
        self.table_models_manager = table_models_manager

    def update_data(self):
        """
        Update this model's data and library.
        """
        self.table_models_manager.update_table_model(self.name())

    # ---- Table edit checks
    def _check_notnull_constraint(self):
        """
        Check that edits do not violate any NOTNULL constraint.
        """
        notnull_colnames = [col.name for col in self.columns() if col.notnull]
        if not len(notnull_colnames):
            return

        added_rows = self._datat.added_rows()
        edited_values = self._datat.edited_values()

        # We check first the new rows added to the database.
        rows_with_null = added_rows[notnull_colnames][
            added_rows[notnull_colnames].isnull().any(axis=1)]
        if not rows_with_null.empty:
            index = rows_with_null.index[0]
            colname = rows_with_null.columns[
                rows_with_null.loc[index].isnull()][0]
            return NotNullTableEditError(index, self.column_at(colname))

        # We check the edits made to existing rows.
        is_null = (
            edited_values
            .loc[(slice(None), notnull_colnames), 'edited_value']
            .isnull())
        if is_null.any():
            index = is_null.index[is_null].get_level_values(0)[0]
            colname = is_null.index[is_null].get_level_values(1)[0]
            return NotNullTableEditError(index, self.column_at(colname))

    def _check_unique_constraint(self):
        """
        Check that edits do not violate any UNIQUE constraint.
        """
        unique_columns = [col for col in self.columns() if col.unique]
        if not len(unique_columns):
            return

        added_rows = self._datat.added_rows()
        edited_values = self._datat.edited_values()
        table_data = self.dataf

        # Drop deleted rows from table data.
        deleted_rows = self._datat.deleted_rows()
        table_data = table_data.drop(deleted_rows, axis=0)

        # Check for unique constraint violation.
        for column in unique_columns:
            column_data = (
                table_data[[column.name] + list(column.unique_subset)]
                .dropna(how='all'))
            column_record = pd.Series(
                data=column_data.to_records(index=False).tolist(),
                index=column_data.index,
                dtype='object')

            column_duplicated = column_record[column_record.duplicated()]
            if column_duplicated.empty:
                continue

            # Check if any duplicated value is in an added row.
            column_added_rows = (
                added_rows[[column.name] + list(column.unique_subset)]
                .dropna(how='all'))
            column_added_record = pd.Series(
                data=column_added_rows.to_records(index=False).tolist(),
                index=column_added_rows.index,
                dtype='object')
            isin_indexes = column_added_record.index[
                column_added_record.isin(column_duplicated.array)]
            if not isin_indexes.empty:
                index = isin_indexes[0]
                return UniqueTableEditError(index, column)

            # Check if any duplicated value is an edited value.
            try:
                column_edited_indexes = (
                    edited_values
                    .loc[(slice(None), column.name), 'edited_value']
                    .index.get_level_values(0))
            except KeyError:
                pass
            else:
                column_edited_data = (
                    table_data.loc[column_edited_indexes]
                    [[column.name] + list(column.unique_subset)]
                    .dropna(how='all'))
                column_edited_record = pd.Series(
                    data=column_edited_data.to_records(index=False).tolist(),
                    index=column_edited_data.index,
                    dtype='object')
                isin_indexes = column_edited_record.index[
                    column_edited_record.isin(column_duplicated.array)]
                if not isin_indexes.empty:
                    index = isin_indexes.get_level_values(0)[0]
                    return UniqueTableEditError(index, column)

            # Else this means the duplicated values were already in the
            # database.

    def _check_foreign_constraint(self, callback):
        """
        Check that edits do not violate any FOREIGN constraint.
        """
        deleted_rows = self._datat.deleted_rows()
        if deleted_rows.empty:
            callback(error=None)
            return

        self.db_connection_manager.add_task(
            'check_foreign_constraints',
            callback=lambda results:
                self._handle_check_foreign_constraints_results(
                    results, callback),
            parent_indexes=deleted_rows,
            data_name=self.__dataname__)
        self.db_connection_manager.run_tasks()

    def _handle_check_foreign_constraints_results(self, results, callback):
        """
        Handle the check foreign constraints results.
        """
        if results is None:
            callback(error=None)
        else:
            parent_index, foreign_colname, foreign_dataname = results
            foreign_tablemodel = (
                self.table_models_manager.find_dataname(foreign_dataname))
            foreign_column = foreign_tablemodel.column_at(foreign_colname)
            callback(ForeignTableEditError(
                parent_index, foreign_column, foreign_tablemodel
                ))

    # ---- SardesTableModel API
    def check_data_edits(self, callback):
        """
        Check that there is no issues with the data edits of this model.
        """
        edit_error = self._check_notnull_constraint()
        if edit_error is not None:
            callback(edit_error)
            return

        edit_error = self._check_unique_constraint()
        if edit_error is not None:
            callback(edit_error)
            return

        # A part of this check is done asynchroneously by the
        # database connection manager, so we cannot fully handle it here.
        self._check_foreign_constraint(callback)

    def save_data_edits(self):
        """
        Save all data edits to the database.
        """
        self.table_models_manager.save_table_model_edits(self.name())

    def confirm_before_saving_edits(self):
        """
        Return wheter we should ask confirmation to the user before saving
        the data edits to the database.
        """
        return self.db_connection_manager.confirm_before_saving_edits()

    def set_confirm_before_saving_edits(self, x):
        """
        Set wheter we should ask confirmation to the user before saving
        the data edits to the database.
        """
        self.db_connection_manager.set_confirm_before_saving_edits(x)
