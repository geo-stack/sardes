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
from time import sleep

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
        print("Connecting to database with {}...".format(
            type(self.db_accessor).__name__))
        self.db_accessor.connect()
        if self.db_accessor._connection_error is None:
            print("Connection to database succeeded.")
        else:
            print("Connection to database failed.")
        return self.db_accessor._connection, self.db_accessor._connection_error

    def _disconnect_from_db(self):
        """Close the connection with the database"""
        print("Closing connection with database...".format(
            type(self.db_accessor).__name__))
        if self.db_accessor is not None:
            self.db_accessor.close_connection()
        print("Connection with database closed.")
        return None,

    # ---- Observation wells
    def _save_observation_well_data(self, sampling_feature_id, attribute_name,
                                    attribute_value):
        """
        Save in the database the new attribute value for the observation well
        corresponding to the specified sampling feature ID.
        """
        self.db_accessor.save_observation_well_data(
            sampling_feature_id, attribute_name, attribute_value)

    def _get_observation_wells_data(self):
        """
        Try to get the list of observation wells that are
        saved in the database.
        """
        print("Fetching observation wells from the database...", end='')
        if self.is_connected():
            try:
                obs_wells = self.db_accessor.get_observation_wells_data()
                print("done")
            except AttributeError as e:
                print("failed")
                print(e)
                obs_wells = DataFrame([])
        else:
            print("failed. No database connection.")
            obs_wells = DataFrame([])
        return obs_wells,

    # ---- Sondes
    def _get_sonde_models_lib(self):
        """
        Try to get the list of sonde models that are saved in the database.
        """
        print("Fetching sonde models library from the database...", end='')
        if self.is_connected():
            try:
                sonde_models = self.db_accessor.get_sonde_models_lib()
                print("done")
            except AttributeError as e:
                print("failed")
                print(e)
                sonde_models = DataFrame([])
        else:
            print("failed. No database connection.")
            sonde_models = DataFrame([])
        return sonde_models,

    def _get_sondes_data(self):
        """
        Try to get the list of sondes that are saved in the database.
        """
        print("Fetching sondes inventory from the database...", end='')
        if self.is_connected():
            try:
                sondes = self.db_accessor.get_sondes_data()
                print("done")
            except AttributeError as e:
                print("failed")
                print(e)
                sondes = DataFrame([])
        else:
            print("failed. No database connection.")
            sondes = DataFrame([])
        return sondes,

    def _save_sonde_data(self, sonde_id, attribute_name, attribute_value):
        """
        Save in the database the new attribute value for the sonde
        corresponding to the specified sonde UID.
        """
        self.db_accessor.save_sonde_data(
            sonde_id, attribute_name, attribute_value)

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
        prop_enum = (' and '.join(monitored_properties) if
                     len(monitored_properties) == 2 else
                     ', '.join(monitored_properties))
        print("Fetching {} data for observation well {}.".format(
            prop_enum, obs_well_id))

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

    # ---- Manual mesurements
    def _get_manual_measurements(self, callback=None, postpone_exec=False):
        """
        Get the list of manual measurements made in the observation wells
        of the monitoring network.
        """
        print("Fetching manual measurements from the database...", end='')
        if self.is_connected():
            try:
                measurements = self.db_accessor.get_manual_measurements()
                print("done")
            except AttributeError as e:
                print("failed")
                print(e)
                measurements = DataFrame([])
        else:
            print("failed. No database connection.")
            measurements = DataFrame([])
        return measurements,


class DatabaseConnectionManager(QObject):
    sig_database_connected = Signal(object, object)
    sig_database_disconnected = Signal()
    sig_database_is_connecting = Signal()
    sig_database_connection_changed = Signal(bool)
    sig_database_data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._task_callbacks = {}
        self._running_tasks = []
        self._queued_tasks = []
        self._pending_tasks = []
        self._task_data = {}

        # Queued tasks are tasks whose execution has not been requested yet.
        # This happens when we want the Worker to execute a list of tasks
        # in a single run. All queued tasks are dumped in the list of pending
        # tasks when `run_task` is called.
        #
        # Pending tasks are tasks whose execution was postponed due to
        # the fact that the worker was busy. These tasks are run as soon
        # as the worker become available.
        #
        # Running tasks are tasks that are being executed by the worker.

        self._db_connection_worker = DatabaseConnectionWorker()
        self._db_connection_thread = QThread()
        self._db_connection_worker.moveToThread(self._db_connection_thread)
        self._db_connection_thread.started.connect(
            self._db_connection_worker.run_tasks)

        # Connect the worker signals to handlers.
        self._db_connection_worker.sig_task_completed.connect(
            self._exec_task_callback)

        self._is_connecting = False
        self._data_changed = False

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
            self.run_tasks()

    def disconnect_from_db(self):
        """Close the connection with the database"""
        self._add_task('disconnect_from_db', self._handle_disconnect_from_db)
        self.run_tasks()

    def run_tasks(self):
        """
        Execute all the tasks that were added to the stack.
        """
        self._run_tasks()

    def close(self):
        """Close this database connection manager."""
        self._db_connection_worker._disconnect_from_db()

    # ---- Observation wells
    def save_observation_well_data(self, sampling_feature_id, attribute_name,
                                   attribute_value, callback=None,
                                   postpone_exec=False):
        """
        Save in the database the new attribute value for the observation well
        corresponding to the specified sampling feature ID.
        """
        self._data_changed = True
        self._add_task('save_observation_well_data',
                       callback,
                       sampling_feature_id,
                       attribute_name,
                       attribute_value)
        if not postpone_exec:
            self.run_tasks()

    def get_observation_wells_data(self, callback):
        """
        Get the list of observation wells that are saved in the database.
        """
        self._add_task('get_observation_wells_data', callback)
        self.run_tasks()

    # ---- Sondes
    def get_sonde_models_lib(self, callback, postpone_exec=False):
        """
        Get the list of sonde models that are saved in the database.
        """
        self._add_task('get_sonde_models_lib', callback)
        if not postpone_exec:
            self.run_tasks()

    def get_sondes_data(self, callback, postpone_exec=False):
        """
        Get the list of sondes that are saved in the database.
        """
        self._add_task('get_sondes_data', callback)
        if not postpone_exec:
            self.run_tasks()

    def save_sonde_data(self, sonde_id, attribute_name, attribute_value,
                        callback=None, postpone_exec=False):
        """
        Save in the database the new attribute value for the sonde
        corresponding to the specified sonde UID.
        """
        self._data_changed = True
        self._add_task('save_sonde_data',
                       callback,
                       sonde_id,
                       attribute_name,
                       attribute_value)
        if not postpone_exec:
            self.run_tasks()

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
        self.run_tasks()

    # ---- Manual mesurements
    def get_manual_measurements(self, callback=None, postpone_exec=False):
        """
        Get the list of manual measurements made in the observation wells
        of the monitoring network.
        """
        self._add_task('get_manual_measurements', callback)
        if not postpone_exec:
            self.run_tasks()

    # ---- Tasks handlers
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
    def _exec_task_callback(self, task_uuid4, returned_values):
        """
        This is the (only) slot that is called after a task is completed
        by the worker.
        """
        # Run the callback associated with the specified task UUID if any.
        if self._task_callbacks[task_uuid4] is not None:
            self._task_callbacks[task_uuid4](*returned_values)

        # Clean up internal variables.
        del self._task_callbacks[task_uuid4]
        del self._task_data[task_uuid4]
        self._running_tasks.remove(task_uuid4)

        if len(self._running_tasks) == 0:
            self._handle_run_tasks_finished()

    def _add_task(self, task, callback, *args, **kargs):
        task_uuid4 = uuid.uuid4()
        self._task_callbacks[task_uuid4] = callback
        self._queued_tasks.append(task_uuid4)
        self._task_data[task_uuid4] = (task, args, kargs)

    def _run_tasks(self):
        """
        Execute all the tasks that were added to the stack.
        """
        self._pending_tasks.extend(self._queued_tasks)
        self._queued_tasks = []
        if len(self._running_tasks) == 0:
            # Even though the worker has done executing all its tasks,
            # we may still need to wait a little for it to stop properly.
            while self._db_connection_thread.isRunning():
                sleep(0.1)

            self._running_tasks = self._pending_tasks
            self._pending_tasks = []
            for task_uuid4 in self._running_tasks:
                task, args, kargs = self._task_data[task_uuid4]
                self._db_connection_worker.add_task(
                    task_uuid4, task, *args, **kargs)
            self._db_connection_thread.start()

    def _handle_run_tasks_finished(self):
        """
        Handle when all tasks that needed to be run by the worker are
        completed.
        """
        if self._data_changed is True:
            self._data_changed = False
            self.sig_database_data_changed.emit()
        if len(self._pending_tasks) > 0:
            self._run_tasks()
