# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Standard imports
import uuid
from collections import OrderedDict

# ---- Third party imports
from pandas import DataFrame
from qtpy.QtCore import QObject, QThread, Signal, Slot


class DatabaseConnectionWorker(QObject):
    """
    A simple worker to create a new database session without blocking the gui.
    """
    sig_task_completed = Signal(object, object)

    def __init__(self, parent=None):
        super(DatabaseConnectionWorker, self).__init__(parent)
        self.db_accessor = None
        self._tasks = OrderedDict()

    # ---- Task management
    def add_task(self, task_uuid4, task, *args, **kargs):
        """
        Add a task to the stack that will be executed when the thread of
        this worker is started.
        """
        self._tasks[task_uuid4] = (task, args, kargs)

    def run_tasks(self):
        """Execute the tasks that were added to the stack."""
        for task_uuid4, (task, args, kargs) in self._tasks.items():
            method_to_exec = getattr(self, '_' + task)
            returned_values = method_to_exec(*args, **kargs)
            self.sig_task_completed.emit(task_uuid4, returned_values)
        self._tasks = OrderedDict()
        self.thread().quit()

    # ---- Worker connection state
    def is_connected(self):
        """Return whether a connection to a database is currently active."""
        return self.db_accessor is not None and self.db_accessor.is_connected()

    # ---- Task definition
    def _connect_to_db(self, db_accessor):
        """Try to create a new connection with the database"""
        self.db_accessor = db_accessor
        self.db_accessor.connect()
        return self.db_accessor._connection, self.db_accessor._connection_error

    def _disconnect_from_db(self):
        """Close the connection with the database"""
        if self.db_accessor is not None:
            self.db_accessor.close_connection()
        return None,

    # ---- Observation wells
    def _get_observation_wells_data(self):
        """
        Try get the list of observation wells that are saved in the database
        and send the results through the sig_observation_wells_fetched
        signal.
        """
        try:
            obs_wells = self.db_accessor.get_observation_wells_data()
        except AttributeError:
            obs_wells = DataFrame([])
        return obs_wells,

    # ---- Monitored properties
    def get_monitored_properties(self):
        """
        Return the list of of properties for which time data is stored in the
        database.
        """
        try:
            monitored_properties = self.db_accessor.monitored_properties
        except AttributeError:
            monitored_properties = []
        return monitored_properties,

    def _get_timeseries_for_obs_well(self, obs_well_id, monitored_properties):
        """
        Get the time data acquired in the observation well for each
        monitored property listed in monitored_properties.
        """
        mprop_list = []
        try:
            for monitored_property in monitored_properties:
                mprop_list.append(
                    self.db_accessor.get_timeseries_for_obs_well(
                        obs_well_id, monitored_property)
                    )
        except AttributeError as error:
            print(type(error).__name__, end=': ')
            print(error)
        return mprop_list,


class DatabaseConnectionManager(QObject):
    sig_database_connected = Signal(object, object)
    sig_database_disconnected = Signal()
    sig_database_is_connecting = Signal()
    sig_database_connection_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._task_callbacks = {}

        self._db_connection_worker = DatabaseConnectionWorker()
        self._db_connection_thread = QThread()
        self._db_connection_worker.moveToThread(self._db_connection_thread)
        self._db_connection_thread.started.connect(
            self._db_connection_worker.run_tasks)

        # Connect the worker signals to handlers.
        self._db_connection_worker.sig_task_completed.connect(
            self._exec_callback)

        self._is_connecting = False

    def is_connected(self):
        """Return whether a connection to a database is currently active."""
        return self._db_connection_worker.is_connected()

    def is_connecting(self):
        """
        Return whether a connection to a database is currently being created.
        """
        return self._is_connecting

    # ---- Public methods
    def connect_to_db(self, db_accessor):
        """
        Try to create a new connection with the database using the
        provided database accessor.
        """
        if db_accessor is not None:
            self._is_connecting = True
            self.sig_database_is_connecting.emit()
            self._add_task(
                'connect_to_db', self._handle_connect_to_db, db_accessor)
            self._db_connection_thread.start()

    def disconnect_from_db(self):
        """Close the connection with the database"""
        self._add_task('disconnect_from_db', self._handle_disconnect_from_db)
        self._db_connection_thread.start()

    # ---- Observation wells
    def get_observation_wells_data(self, callback):
        """
        Get the list of observation wells that are saved in the database.

        The results are sent through the sig_database_observation_wells signal
        as a pandas DataFrame.
        """
        self._add_task('get_observation_wells_data', callback)
        self._db_connection_thread.start()

    # ---- Monitored properties
    def get_monitored_properties(self, callback=None):
        """
        Get the list of of properties for which time data is stored in the
        database.
        """
        monitored_properties = (
            self._db_connection_worker.get_monitored_properties())
        if callback is not None:
            callback(monitored_properties)
        return monitored_properties

    def get_timeseries_for_obs_well(self, obs_well_id, monitored_properties,
                                    callback):
        """
        Get the time data acquired in the observation well for each
        monitored property in the list.
        """
        if isinstance(monitored_properties, str):
            monitored_properties = [monitored_properties, ]
        self._add_task('get_timeseries_for_obs_well', callback,
                       obs_well_id, monitored_properties)
        self._db_connection_thread.start()

    # ---- Handlers
    @Slot(object, object)
    def _handle_connect_to_db(self, connection, connection_error):
        """
        Handle when a connection to the database was created successfully
        or not.
        """
        self._is_connecting = False
        self.sig_database_connected.emit(connection, connection_error)
        self.sig_database_connection_changed.emit(self.is_connected())

    @Slot()
    def _handle_disconnect_from_db(self, *args, **kargs):
        """
        Handle when the connection to the database was closed successfully.
        """
        self.sig_database_disconnected.emit()
        self.sig_database_connection_changed.emit(self.is_connected())

    @Slot(object, object)
    def _exec_callback(self, task_uuid4, returned_values):
        if self._task_callbacks[task_uuid4] is not None:
            self._task_callbacks[task_uuid4](*returned_values)
        del self._task_callbacks[task_uuid4]

    def _add_task(self, task, callback, *args, **kargs):
        task_uuid4 = uuid.uuid4()
        self._task_callbacks[task_uuid4] = callback
        self._db_connection_worker.add_task(task_uuid4, task, *args, **kargs)
