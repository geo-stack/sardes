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
    from sardes.database.database_manager import DatabaseConnectionManager

# ---- Standard imports
import os
import os.path as osp
import tempfile

# ---- Third party imports
from qtpy.QtCore import QObject, Signal
from qtpy.QtWidgets import QMenu, QFileDialog

# ---- Local imports
from sardes.config.gui import get_iconsize
from sardes.config.main import TEMP_DIR
from sardes.config.ospath import (
    get_select_file_dialog_dir, set_select_file_dialog_dir)
from sardes.utils.qthelpers import create_toolbutton, create_action


class SardesTableModelsManager(QObject):
    """
    A manager to handle data updating and saving of Sardes table models.
    """
    sig_models_data_changed = Signal()

    def __init__(self, db_manager: DatabaseConnectionManager):
        super().__init__()
        # A dictionary containing the table models registered to this manager
        # using as key the name of the models.
        self._table_models = {}

        # A dictionary mapping the name of the data being displayed for each
        # table model registered to this manager.
        self._dataname_map = {}

        # Contains the lists of data and libraries that need to be updated
        # for each table registered to this manager when the update_table
        # is called.
        self._queued_model_updates = {}
        #
        # Contains the lists of data and library names that are currently
        # being updated after the update_table was called.
        self._running_model_updates = {}

        # Setup the database manager.
        self.db_manager = db_manager
        db_manager.sig_database_connection_changed.connect(
            self._handle_db_connection_changed)
        db_manager.sig_database_data_changed.connect(
            self._handle_database_data_changed)

    # ---- Public API
    def table_models(self):
        """Return the list of table models registered to this manager."""
        return list(self._table_models.values())

    def find_dataname(self, dataname):
        """
        Return the table model registered to this manager that is used to
        display the data referenced as 'name' in the database connection
        manager.
        """
        return self._dataname_map[dataname]

    def register_table_model(self, table_model):
        """
        Register a new sardes table model to the manager.
        """
        if table_model.name() in self._table_models:
            raise Warning("There is already a table model named '{}' "
                          "registered to the Sardes table manager."
                          .format(table_model.name()))
            return
        if table_model.__dataname__ in self._dataname_map:
            raise Warning("There is already a table model registered to the "
                          "Sardes table manager that displays '{}' data."
                          .format(table_model.name()))
            return
        table_model.set_table_models_manager(self)
        self._dataname_map[table_model.__dataname__] = table_model
        self._table_models[table_model.name()] = table_model
        self._queued_model_updates[table_model.name()] = (
            [table_model.__dataname__] + table_model.__libnames__)
        self._running_model_updates[table_model.name()] = []

    def update_table_model(self, table_name: str):
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
                    callback=lambda dataf:
                        self._update_table_model_callback(dataf, table_name),
                    postpone_exec=True)
            self._queued_model_updates[table_name] = []
            self.db_manager.run_tasks()

    def save_table_model_edits(self, table_name: str):
        """
        Save the changes made to table 'table_name' in the database.
        """
        if table_name not in self._table_models:
            raise Warning("Warning: Table model '{}' is not registered."
                          .format(table_name))
            return

        tablemodel = self._table_models[table_name]
        tablemodel.sig_data_about_to_be_saved.emit()
        self.db_manager.add_task(
            'save_table_edits',
            callback=self._save_table_model_edits_callback,
            name=tablemodel.__dataname__,
            deleted_rows=tablemodel.tabledata().deleted_rows(),
            added_rows=tablemodel.tabledata().added_rows(),
            edited_values=tablemodel.tabledata().edited_values()
            )
        self.db_manager.run_tasks()

    # ---- Private API
    def _save_table_model_edits_callback(self, dataf):
        """
        A callback that handles when edits made to a table model have been
        saved in the database.
        """
        data_name = dataf.attrs['name']
        table_model = self.find_dataname(data_name)
        table_model.sig_data_saved.emit()

        # We add 'data_name' to '_running_model_updates' to prevent the data
        # of the corresponding table model from being updated a second time
        # unecessarily.
        #
        # Concretely, after 'db_manager.sig_database_data_changed' is emitted,
        # this prevents 'data_name' from being added to '_queued_model_updates'
        # in '_handle_database_data_changed'. This thus prevents an unecessary
        # update of the table model's data when 'update_table_model'
        # is called from the plugin side after 'sig_models_data_changed' is
        # emitted in '_handle_database_data_changed'.

        self._running_model_updates[table_model.name()].append(data_name)

        table_model.sig_data_about_to_be_updated.emit()
        table_model.set_model_data(dataf)
        table_model.sig_data_updated.emit()

        self.db_manager.sig_database_data_changed.emit([data_name])
        self._running_model_updates[table_model.name()].remove(data_name)

    def _update_table_model_callback(self, dataf, table_name):
        """
        A callback used in 'update_table_model' to set the data or library
        of a table model.
        """
        data_name = dataf.attrs['name']
        table_model = self._table_models[table_name]

        if data_name == table_model.__dataname__:
            # Update the data of the table model.
            table_model.set_model_data(dataf)
        elif data_name in table_model.__libnames__:
            # Update the corresponding library of the table model.
            table_model.set_model_library(dataf, data_name)

        self._running_model_updates[table_name].remove(data_name)
        if not len(self._running_model_updates[table_name]):
            table_model.sig_data_updated.emit()

    def _handle_database_data_changed(self, data_changed):
        """
        Handle when changes are made to the database.

        Note that changes made to the database outside of Sardes are not
        taken into account here.

        Parameters
        ----------
        data_changed : list of str
            A list of table data names that were changed in the database.
        """
        for table_name, table_model in self._table_models.items():
            data_libs_names = (
                [table_model.__dataname__] + table_model.__libnames__)
            self._queued_model_updates[table_name].extend([
                name for name in data_changed if
                (name in data_libs_names and
                 name not in self._queued_model_updates[table_name] and
                 name not in self._running_model_updates[table_name])
                ])
        self.sig_models_data_changed.emit()

    def _handle_db_connection_changed(self, is_connected):
        """
        Handle when the connection to the database changes.
        """
        if is_connected:
            for table_name, table_model in self._table_models.items():
                self._queued_model_updates[table_name] = (
                    [table_model.__dataname__] + table_model.__libnames__)
        else:
            for table_name, table_model in self._table_models.items():
                self._queued_model_updates[table_name] = []
                table_model.clear_data()
        self.sig_models_data_changed.emit()


class FileAttachmentManager(QObject):
    """
    A class to handle adding, viewing, and removing file attachments
    in the database.
    """
    sig_attach_request = Signal(object, object, object)

    sig_attachment_added = Signal()
    sig_attachment_shown = Signal()
    sig_attachment_removed = Signal()

    def __init__(self, tablewidget, icon, attachment_type,
                 qfiledialog_namefilters, qfiledialog_title,
                 text, tooltip, attach_text, attach_tooltip, show_text,
                 show_tooltip, remove_text, remove_tooltip):
        super().__init__()
        self._enabled = True
        self.dbmanager = None

        self.tablewidget = tablewidget
        self.attachment_type = attachment_type

        self.qfiledialog_namefilters = qfiledialog_namefilters
        self.qfiledialog_title = qfiledialog_title

        self.toolbutton = create_toolbutton(
            tablewidget, text=text, tip=tooltip, icon=icon,
            iconsize=get_iconsize())
        self.attach_action = create_action(
            tablewidget, text=attach_text, tip=attach_tooltip,
            icon='attachment', triggered=self._handle_attach_request)
        self.show_action = create_action(
            tablewidget, text=show_text, tip=show_tooltip,
            icon='magnifying_glass', triggered=self._handle_show_request)
        self.remove_action = create_action(
            tablewidget, text=remove_text, tip=remove_tooltip,
            icon='delete_data', triggered=self._handle_remove_request)

        menu = QMenu()
        menu.addAction(self.attach_action)
        menu.addAction(self.show_action)
        menu.addAction(self.remove_action)
        menu.aboutToShow.connect(self._handle_menu_aboutToShow)

        self.toolbutton.setMenu(menu)
        self.toolbutton.setPopupMode(self.toolbutton.InstantPopup)

    # ---- Qt widget interface emulation
    def isEnabled(self):
        """
        Treturn whether this file attachment manager is enabled.
        """
        return self._enabled

    def setEnabled(self, enabled):
        """
        Set this file attachment manager state to the provided enabled value.
        """
        self._enabled = bool(enabled)
        self.toolbutton.setEnabled(self._enabled)

    def set_dbmanager(self, dbmanager):
        """
        Set the database manager for this file attachment manager.
        """
        self.dbmanager = dbmanager

    # ---- Convenience Methods
    def current_station_id(self):
        """
        Return the id of the station that is currently selected
        in the table in which this file attachment manager is installed.
        """
        station_data = self.tablewidget.get_current_obs_well_data()
        if station_data is None:
            return None
        else:
            return station_data.name

    def current_station_name(self):
        """
        Return the name of the station that is currently selected
        in the table in which this file attachment manager is installed.
        """
        station_data = self.tablewidget.get_current_obs_well_data()
        return station_data['obs_well_id']

    def is_attachment_exists(self):
        """
        Return whether an attachment exists in the database for the
        currently selected station in the table.
        """
        return bool((
            self.tablewidget.model().libraries['attachments_info'] ==
            [self.current_station_id(), self.attachment_type]
            ).all(1).any())

    # ---- Handlers
    def _handle_menu_aboutToShow(self):
        """
        Handle when the menu is about to be shown so that we can
        disable/enable the items depending on the availability or
        not of an attachment for the currently selected station.
        """
        self.tablewidget.tableview.setFocus()
        station_id = self.current_station_id()
        if station_id is None:
            self.attach_action.setEnabled(False)
            self.show_action.setEnabled(False)
            self.remove_action.setEnabled(False)
        else:
            is_attachment_exists = self.is_attachment_exists()
            self.attach_action.setEnabled(True)
            self.show_action.setEnabled(is_attachment_exists)
            self.remove_action.setEnabled(is_attachment_exists)

    def _handle_attach_request(self):
        """
        Handle when a request is made by the user to add an attachment
        to the currently selected station.
        """
        filename, filefilter = QFileDialog.getOpenFileName(
            self.tablewidget.parent() or self.tablewidget,
            self.qfiledialog_title.format(self.current_station_name()),
            get_select_file_dialog_dir(),
            self.qfiledialog_namefilters)
        if filename:
            set_select_file_dialog_dir(osp.dirname(filename))
            if self.dbmanager is not None:
                station_id = self.current_station_id()
                self.dbmanager.set_attachment(
                    station_id, self.attachment_type, filename,
                    callback=self.sig_attachment_added.emit)

    def _handle_show_request(self):
        """
        Handle when a request is made by the user to show the attachment
        of the currently selected station.
        """
        if self.dbmanager is not None:
            station_id = self.current_station_id()
            self.dbmanager.get_attachment(
                station_id,
                self.attachment_type,
                callback=self._open_attachment_in_external)

    def _handle_remove_request(self):
        """
        Handle when a request is made by the user to remove the attachment
        of the currently selected station.
        """
        if self.dbmanager is not None:
            station_id = self.current_station_id()
            self.dbmanager.del_attachment(
                station_id,
                self.attachment_type,
                callback=self.sig_attachment_removed.emit)

    # ---- Callbacks
    def _open_attachment_in_external(self, data, name):
        """
        Open the attachment file in an external application that is
        chosen by the OS.
        """
        temp_path = tempfile.mkdtemp(dir=TEMP_DIR)
        temp_filename = osp.join(temp_path, name)
        with open(temp_filename, 'wb') as f:
            f.write(data)
        os.startfile(temp_filename)
        self.sig_attachment_shown.emit()
