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
import datetime

# ---- Third party imports
import pandas as pd
from pandas import DataFrame
from qtpy.QtCore import QObject, QThread, Signal, Slot

# ---- Local imports
from sardes.api.timeseries import DataType


class DatabaseConnectionWorker(QObject):
    """
    A simple worker to create a new database session without blocking the gui.
    """
    sig_task_completed = Signal(object, object)

    def __init__(self, parent=None):
        super(DatabaseConnectionWorker, self).__init__(parent)
        self.db_accessor = None
        self._tasks = OrderedDict()

        # Setup a cache structure for the tables and libraries.
        self._cache = {}

    def clear_cache(self):
        """
        Clear the cache for the tables and libraries data.
        """
        print("Clearing the database worker cache... done.")
        self._cache = {}

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
        self.clear_cache()
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
        self.clear_cache()
        print("Closing connection with database...".format(
            type(self.db_accessor).__name__))
        if self.db_accessor is not None:
            self.db_accessor.close_connection()
        print("Connection with database closed.")
        return None,

    # ---- Add, Get, Set data
    def _add(self, name, *args, **kargs):
        """
        Add a new item to the data related to name in the database.
        """
        if name in self._cache:
            del self._cache[name]
        self.db_accessor.add(name, *args, **kargs)

    def _get(self, name, *args, **kargs):
        """
        Get the data related to name from the database.
        """
        if name in self._cache:
            print("Fetched '{}' from store.".format(name))
            return self._cache[name],

        print("Fetching '{}' from the database...".format(name), end='')
        if self.is_connected():
            try:
                data = self.db_accessor.get(name, *args, **kargs)
                print("done")
            except Exception as e:
                print("failed because of the following error.")
                print(e)
                print('-' * 20)
                data = DataFrame([])
            else:
                self._cache[name] = data
        else:
            print("failed because not connected to a database.")
            data = DataFrame([])
        return data,

    def _delete(self, name, *args, **kargs):
        """
        Delete an item related to name from the database.
        """
        if name in self._cache:
            del self._cache[name]
        self.db_accessor.delete(name, *args, **kargs)

    def _create_index(self, name):
        """
        Return a new index that can be used subsequently to add new item
        to the data related to name in the database.
        """
        return self.db_accessor.create_index(name)

    def _set(self, name, *args, **kargs):
        """
        Save the data related to name in the database.
        """
        if name in self._cache:
            del self._cache[name]
        self.db_accessor.set(name, *args, **kargs)

    # ---- Timeseries
    def _get_timeseries_for_obs_well(self, sampling_feature_uuid, data_types):
        """
        Get the time data acquired in the observation well for each
        given data type.
        """
        data_types = [DataType(data_type) for data_type in data_types]
        obs_well_data = self._get('observation_wells_data')[0]
        obs_well_data = obs_well_data.loc[sampling_feature_uuid]

        # Print some info message in the console.
        prop_names = [prop.name for prop in data_types]
        prop_enum = (' and '.join(prop_names) if
                     len(prop_names) == 2 else ', '.join(prop_names))
        print("Fetching {} data for observation well {}.".format(
            prop_enum, obs_well_data['obs_well_id']))

        # Fetch the data.
        readings = None
        tseries_groups = []
        date_types = []
        try:
            for data_type in data_types:
                tseries_dataf = self.db_accessor.get_timeseries_for_obs_well(
                    sampling_feature_uuid, data_type)
                tseries_groups.append(tseries_dataf)

                if tseries_dataf.empty:
                    continue
                if readings is None:
                    readings = tseries_dataf
                else:
                    readings = readings.merge(
                        tseries_dataf,
                        left_on=['datetime', 'obs_id', 'sonde_id',
                                 'install_depth'],
                        right_on=['datetime', 'obs_id', 'sonde_id',
                                  'install_depth'],
                        how='outer', sort=True)
                date_types.append(data_type)
            if readings is None:
                readings = DataFrame(
                    [],
                    columns=['datetime', 'sonde_id', DataType(0),
                             DataType(1), DataType(2), 'install_depth',
                             'obs_id'])

            # Reorder the columns so that the data are displayed nicely.
            readings = readings[
                ['datetime', 'sonde_id'] +
                date_types +
                ['install_depth', 'obs_id']]
            readings = readings.sort_values('datetime', axis=0, ascending=True)

            # Add metadata to the dataframe.
            readings._metadata = ['sampling_feature_data']
            readings.sampling_feature_data = obs_well_data
        except Exception as error:
            print(type(error).__name__, end=': ')
            print(error)
        return readings,

    def _save_timeseries_data_edits(self, tseries_edits):
        """
        Save in the database a set of edits that were made to to timeseries
        data that were already saved in the database.
        """
        print("Saving timeseries data edits...")
        if 'observation_wells_data_overview' in self._cache:
            del self._cache['observation_wells_data_overview']
        self.db_accessor.save_timeseries_data_edits(tseries_edits)
        print("...timeseries data edits saved sucessfully.")

    def _add_timeseries_data(self, tseries_data, obs_well_uuid,
                             sonde_installation_uuid):
        """
        Save in the database a set of timeseries data associated with the
        given well and sonde installation id.
        """
        print("Saving timeseries data...")
        if 'observation_wells_data_overview' in self._cache:
            del self._cache['observation_wells_data_overview']
        self.db_accessor.add_timeseries_data(
            tseries_data, obs_well_uuid, sonde_installation_uuid)
        print("...timeseries data edits saved sucessfully.")

    def _delete_timeseries_data(self, tseries_dels):
        """
        Delete data in the database for the observation IDs, datetime and
        data type specified in tseries_dels.
        """
        print("Deleting timeseries data...")
        if 'observation_wells_data_overview' in self._cache:
            del self._cache['observation_wells_data_overview']
        self.db_accessor.delete_timeseries_data(tseries_dels)
        print("...timeseries data deleted sucessfully.")

    # ---- Utilities
    def _get_sonde_installation_info(self, sonde_serial_no, date_time):
        """
        Fetch and return from the database the installation infos related to
        the given sonde serial number and datetime.
        """
        if not self.is_connected():
            return None,

        sonde_data = self._get('sondes_data')[0]
        try:
            sonde_uuid = (
                sonde_data[sonde_data['sonde_serial_no'] == sonde_serial_no]
                .index[0])
        except (KeyError, IndexError):
            return None,

        sonde_installations = self._get('sonde_installations')[0]
        try:
            installs = (
                sonde_installations
                [sonde_installations['sonde_uuid'] == sonde_uuid]
                )
        except (KeyError, IndexError):
            return None,
        else:
            for i in range(len(installs)):
                sonde_install = installs.iloc[i].copy()
                start_date = sonde_install['start_date']
                end_date = (sonde_install['end_date'] if
                            not pd.isnull(sonde_install['end_date']) else
                            datetime.datetime.now())
                if start_date <= date_time and end_date >= date_time:
                    break
            else:
                return None,

        # Add information about well name and municipality.
        obs_wells_data = self._get('observation_wells_data')[0]
        obs_well_uuid = sonde_install['sampling_feature_uuid']
        sonde_install['well_name'] = obs_wells_data.at[
            obs_well_uuid, 'obs_well_id']
        sonde_install['well_municipality'] = obs_wells_data.at[
            obs_well_uuid, 'municipality']

        # Add sonde brand and model info.
        sonde_model_id = sonde_data.loc[sonde_uuid]['sonde_model_id']
        sonde_models_lib = self._get('sonde_models_lib')[0]
        sonde_install['sonde_brand_model'] = sonde_models_lib.loc[
            sonde_model_id, 'sonde_brand_model']

        return sonde_install,


class SardesModelsManager(QObject):
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

    # ---- Public API
    def register_model(self, table_model, data_name, lib_names=None):
        """
        Register a new sardes table model to the manager.
        """
        lib_names = lib_names or []
        table_id = table_model._table_id
        self._table_models[table_id] = table_model
        self._models_req_data[table_id] = [data_name] + lib_names
        self._queued_model_updates[table_id] = [data_name] + lib_names
        self._running_model_updates[table_id] = []

    def update_model(self, table_id):
        """
        Update the given sardes data model and libraries.
        """
        if table_id not in self._table_models:
            raise Warning("Warning: Table model '{}' is not registered."
                          .format(table_id))
            return

        if len(self._queued_model_updates[table_id]):
            self._table_models[table_id].sig_data_about_to_be_updated.emit()
            for name in self._queued_model_updates[table_id]:
                self._running_model_updates[table_id].append(name)
                self.db_manager.get(
                    name,
                    callback=lambda dataf, name=name:
                        self._set_model_data_or_lib(dataf, name, table_id),
                    postpone_exec=True)
            self._queued_model_updates[table_id] = []
            self.db_manager.run_tasks()

    def save_model_edits(self, table_id):
        """
        Save all data edits to the database.
        """
        table_model = self._table_models[table_id]
        table_model.sig_data_about_to_be_saved.emit()
        table_model_data_name = self._models_req_data[table_id][0]
        for edit in table_model._datat.edits():
            callback = (table_model.sig_data_saved.emit
                        if edit == table_model._datat.edits()[-1] else None)
            if edit.type() == table_model.ValueChanged:
                self.db_manager.set(
                    table_model_data_name,
                    edit.index, edit.column, edit.edited_value,
                    callback=callback,
                    postpone_exec=True)
            elif edit.type() == table_model.RowAdded:
                self.db_manager.add(
                    table_model_data_name,
                    edit.index, edit.values,
                    callback=callback,
                    postpone_exec=True)
            elif edit.type() == table_model.RowDeleted:
                self.db_manager.delete(
                    table_model_data_name,
                    edit.index,
                    callback=callback,
                    postpone_exec=True)
            else:
                raise TypeError('Edit type not recognized.')
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


class DatabaseConnectionManager(QObject):
    sig_database_connected = Signal(object, object)
    sig_database_disconnected = Signal()
    sig_database_is_connecting = Signal()
    sig_database_connection_changed = Signal(bool)
    sig_database_data_changed = Signal(list)
    sig_tseries_data_changed = Signal(list)
    sig_run_tasks_finished = Signal()
    sig_models_data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_connecting = False
        self._data_changed = set()
        self._tseries_data_changed = set()

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

        # Setup the table models manager.
        self.models_manager = SardesModelsManager(self)
        self.models_manager.sig_models_data_changed.connect(
            self.sig_models_data_changed.emit)
        self._confirm_before_saving_edits = True

    def is_connected(self):
        """Return whether a connection to a database is currently active."""
        return self._db_connection_worker.is_connected()

    def is_connecting(self):
        """
        Return whether a connection to a database is currently being created.
        """
        return self._is_connecting

    # ---- Public methods
    def add(self, *args, callback=None, postpone_exec=False):
        """
        Add a new item to the data related to name in the database.
        """
        self._data_changed.add(args[0])
        self._add_task('add', callback, *args)
        if not postpone_exec:
            self.run_tasks()

    def get(self, *args, callback=None, postpone_exec=False):
        """
        Get the data related to name from the database.
        """
        self._add_task('get', callback, *args)
        if not postpone_exec:
            self.run_tasks()

    def delete(self, *args, callback=None, postpone_exec=False):
        """
        Delete an item related to name from the database.
        """
        self._data_changed.add(args[0])
        self._add_task('delete', callback, *args)
        if not postpone_exec:
            self.run_tasks()

    def create_index(self, name):
        """
        Return a new index that can be used subsequently to add new item
        to the data related to name in the database.
        """
        return self._db_connection_worker._create_index(name)

    def set(self, *args, callback=None, postpone_exec=False):
        """
        Set the data related to name in the database.
        """
        self._data_changed.add(args[0])
        self._add_task('set', callback, *args)
        if not postpone_exec:
            self.run_tasks()

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
        self.disconnect_from_db()

    # ---- Utilities
    def get_sonde_installation_info(self, sonde_serial_no, date_time,
                                    callback=None, postpone_exec=False):
        """
        Fetch and return from the database the installation infos related to
        the given sonde serial number and datetime.
        """
        self._add_task('get_sonde_installation_info', callback,
                       sonde_serial_no, date_time)
        self.run_tasks()

    # ---- Timeseries
    def get_timeseries_for_obs_well(
            self, obs_well_id, data_types, callback=None, postpone_exec=False,
            main_thread=False):
        """
        Get the time data acquired in the observation well for each
        given data type.
        """
        if main_thread is False:
            self._add_task('get_timeseries_for_obs_well', callback,
                           obs_well_id, data_types)
            if not postpone_exec:
                self.run_tasks()
        else:
            tseries_groups = (
                self._db_connection_worker._get_timeseries_for_obs_well(
                    obs_well_id, data_types)
                )[0]
            if callback is not None:
                callback(tseries_groups)
            return tseries_groups

    def save_timeseries_data_edits(self, tseries_edits, obs_well_id,
                                   callback=None, postpone_exec=False):
        """
        Save in the database a set of edits that were made to timeseries
        data that were already saved in the database.

        Parameters
        ----------
        tseries_edits: pandas.DataFrame
            A multi-indexes pandas dataframe that contains the edited
            numerical values that need to be saved in the database.
            The indexes of the dataframe correspond, respectively, to the
            datetime (datetime), observation ID (str) and the data type
            (DataType) corresponding to the edited value.
       obs_well_id: object
            A unique identifier used to reference the observation well in
            the database for which time series data will be edited.
        """
        self._data_changed.add('observation_wells_data_overview')
        self._tseries_data_changed.add(obs_well_id)
        self._add_task('save_timeseries_data_edits', callback, tseries_edits)
        if not postpone_exec:
            self.run_tasks()

    def add_timeseries_data(self, tseries_data, obs_well_id,
                            sonde_installation_uuid=None, callback=None,
                            postpone_exec=False):
        """
        Save in the database a set of timeseries data associated with the
        given well and sonde installation id.

        Parameters
        ----------
        tseries_data: pandas.DataFrame
            A pandas dataframe where time is saved as datetime in a column
            named 'datetime'. The columns in which the numerical values are
            saved must be a member of :class:`sardes.api.timeseries.DataType`
            enum.
        obs_well_id: object
            A unique identifier used to reference the observation well in
            the database for which time series data will be added.
        """
        self._data_changed.add('observation_wells_data_overview')
        self._tseries_data_changed.add(obs_well_id)
        self._add_task('add_timeseries_data', callback, tseries_data,
                       obs_well_id, sonde_installation_uuid)
        if not postpone_exec:
            self.run_tasks()

    def delete_timeseries_data(self, tseries_dels, obs_well_id, callback=None,
                               postpone_exec=False):
        """
        Delete data in the database for the observation IDs, datetime and
        data type specified in tseries_dels.

        Parameters
        ----------
        tseries_dels: pandas.DataFrame
            A pandas dataframe that contains the observation IDs, datetime,
            and datatype for which timeseries data need to be deleted
            from the database.
        obs_well_id: object
            A unique identifier used to reference the observation well in
            the database for which time series data will be deleted.
        """
        self._data_changed.add('observation_wells_data_overview')
        self._tseries_data_changed.add(obs_well_id)
        self._add_task('delete_timeseries_data', callback, tseries_dels)
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
            try:
                self._task_callbacks[task_uuid4](*returned_values)
            except TypeError:
                self._task_callbacks[task_uuid4]()

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
            # Even though the worker has executed all its tasks,
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
        if len(self._data_changed):
            self.sig_database_data_changed.emit(list(self._data_changed))
            self._data_changed = set()
        if len(self._tseries_data_changed):
            self.sig_tseries_data_changed.emit(
                list(self._tseries_data_changed))
            self._tseries_data_changed = set()
        if len(self._pending_tasks) > 0:
            self._run_tasks()
        else:
            self.sig_run_tasks_finished.emit()

    # ---- Tables
    def create_new_model_index(self, table_id):
        """
        Return a new index that can be used subsequently to add new item
        to a Sardes model.
        """
        name = self.models_manager._models_req_data[table_id][0]
        return self.create_index(name)

    def register_model(self, table_model, data_name, lib_names=None):
        """
        Register a new sardes table model to the manager.
        """
        table_model.set_database_connection_manager(self)
        self.models_manager.register_model(
            table_model, data_name, lib_names)

    def update_model(self, table_id):
        """
        Update the given sardes data model and libraries.
        """
        self.models_manager.update_model(table_id)

    def save_model_edits(self, table_id):
        """
        Save all data edits to the database.
        """
        self.models_manager.save_model_edits(table_id)


if __name__ == '__main__':
    from sardes.database.accessor_sardes_lite import (
        DatabaseAccessorSardesLite)
    from sardes.api.timeseries import DataType

    db_accessor = DatabaseAccessorSardesLite(
        'D:/rsesq_prod_sample_2020-03-04.db')
    dbmanager = DatabaseConnectionManager()
    dbmanager.connect_to_db(db_accessor)
    sampling_feature_uuid = (
        db_accessor._get_sampling_feature_uuid_from_name('01070001'))

    readings = dbmanager.get_timeseries_for_obs_well(
        sampling_feature_uuid,
        [DataType.WaterLevel, DataType.WaterTemp],
        callback=None,
        postpone_exec=False, main_thread=True)
    print(readings)
