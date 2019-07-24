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
from pandas import DataFrame
from qtpy.QtCore import QObject, QThread, Signal, Slot


class DatabaseConnectionWorker(QObject):
    """
    A simple worker to create a new database session without blocking the gui.
    """
    sig_database_connected = Signal(object, object)
    sig_database_disconnected = Signal()
    sig_database_observation_wells = Signal(DataFrame)

    def __init__(self, parent=None):
        super(DatabaseConnectionWorker, self).__init__(parent)
        self.db_accessor = None

        self.database = ""
        self.user = ""
        self.password = ""
        self.host = ""
        self.port = 5432
        self.client_encoding = 'utf_8'

        self._tasks = []

    def add_task(self, task, *args, **kargs):
        """
        Add a task to the stack that will be executed when the thread of
        this worker is started.
        """
        self._tasks.append((task, args, kargs))

    def run_tasks(self):
        """Execute the tasks that were added to the stack."""
        for task, args, kargs in self._tasks:
            method_to_exec = getattr(self, task)
            method_to_exec(*args, **kargs)
        self._tasks = []
        self.thread().quit()

    def is_connected(self):
        """Return whether a connection to a database is currently active."""
        return self.db_accessor is not None and self.db_accessor.is_connected()

    def connect_to_db(self, db_accessor):
        """Try to create a new connection with the database"""
        self.db_accessor = db_accessor
        self.db_accessor.connect()
        self.sig_database_connected.emit(
            self.db_accessor._connection, self.db_accessor._connection_error)

    def disconnect_from_db(self):
        """Close the connection with the database"""
        if self.db_accessor is not None:
            self.db_accessor.close_connection()
        self.sig_database_disconnected.emit()

    def get_observation_wells(self):
        """
        Try get the list of observation wells that are saved in the database
        and send the results through the sig_database_observation_wells
        signal.
        """
        try:
            locations = self.db_accessor.get_observation_wells()
        except AttributeError:
            locations = DataFrame([])
        self.sig_database_observation_wells.emit(locations)

    def execute_sql_request(self, sql_request, **kwargs):
        """Execute a SQL statement construct and return a ResultProxy."""
        if self.db_accessor is not None:
            return self.db_accessor.execute(sql_request, **kwargs)


class DatabaseConnectionManager(QObject):
    sig_database_connected = Signal(object, object)
    sig_database_disconnected = Signal()
    sig_database_connection_changed = Signal(bool)
    sig_database_observation_wells = Signal(DataFrame)
    sig_new_database_accessor_registered = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._db_accessors = {}

        self._db_connection_worker = DatabaseConnectionWorker()
        self._db_connection_thread = QThread()
        self._db_connection_worker.moveToThread(self._db_connection_thread)
        self._db_connection_thread.started.connect(
            self._db_connection_worker.run_tasks)

        # Connect the worker signals to handlers.
        self._db_connection_worker.sig_database_connected.connect(
            self._handle_connect_to_db)
        self._db_connection_worker.sig_database_disconnected.connect(
            self._handle_disconnect_from_db)
        self._db_connection_worker.sig_database_observation_wells.connect(
            self._handle_get_observation_wells)

        self._db_connection_worker.sig_database_connected.connect(
            lambda: self.sig_database_connection_changed.emit(
                self.is_connected()))
        self._db_connection_worker.sig_database_disconnected.connect(
            lambda: self.sig_database_connection_changed.emit(
                self.is_connected()))

        self._is_connecting = False
        self._locations = []

    def is_connected(self):
        """Return whether a connection to a database is currently active."""
        return self._db_connection_worker.is_connected()

    def is_connecting(self):
        """
        Return whether a connection to a database is currently being created.
        """
        return self._is_connecting

    @Slot(object, object)
    def _handle_connect_to_db(self, connection, connection_error):
        """
        Handle when a connection to the database was created successfully
        or not.
        """
        self._is_connecting = False
        self.sig_database_connected.emit(connection, connection_error)

    def connect_to_db(self, db_accessor):
        """
        Try to create a new connection with the database using the
        provided database accessor.
        """
        self._is_connecting = True
        self._db_connection_worker.add_task('connect_to_db', db_accessor)
        self._db_connection_thread.start()

    @Slot()
    def _handle_disconnect_from_db(self):
        """
        Handle when the connection to the database was closed successfully.
        """
        self.sig_database_disconnected.emit()

    def disconnect_from_db(self):
        """Close the connection with the database"""
        self._db_connection_worker.add_task('disconnect_from_db')
        self._db_connection_thread.start()

    @Slot(DataFrame)
    def _handle_get_observation_wells(self, locations):
        """
        Handle when the list of observation wells saved in the database
        was fetched successfully.
        """
        self._locations = locations
        self.sig_database_observation_wells.emit(self._locations)

    def get_observation_wells(self):
        """
        Get the list of observation wells that are saved in the database.

        The results are sent through the sig_database_observation_wells signal
        as a list of ObservationWell objects.
        """
        self._db_connection_worker.add_task('get_observation_wells')
        self._db_connection_thread.start()
