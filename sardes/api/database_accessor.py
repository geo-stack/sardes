# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports
from abc import ABC, abstractmethod

# ---- Third party imports
from pandas import Series, DataFrame

# ---- Local imports
from sardes.api.timeseries import TimeSeriesGroup, TimeSeries


class DatabaseAccessorBase(ABC):
    """
    Basic functionality for Sardes database accessor.

    WARNING: Don't override any methods or attributes present here unless you
    know what you are doing.
    """

    def __init__(self):
        self._connection = None
        self._connection_error = None
        self._temp_indexes = {}

    # ---- Public API
    def get(self, name, *args, **kargs):
        """
        Get the data related to name from the database.
        """
        method_to_exec = getattr(self, 'get_' + name)
        result = method_to_exec(*args, **kargs)
        try:
            result.name = name
        except AttributeError:
            pass
        return result

    def set(self, name, *args, **kargs):
        """
        Save the data related to name in the database.
        """
        getattr(self, 'set_' + name)(*args, **kargs)

    def add(self, name, primary_key, values={}):
        """
        Add a new item to the data related to name in the database using
        the given primary_key and values.
        """
        getattr(self, 'add_' + name)(primary_key, values)
        self.del_temp_index(name, primary_key)

    def create_index(self, name):
        """
        Return a new index that can be used subsequently to add a new item
        related to name in the database.
        """
        new_index = self._create_index(name)
        self.add_temp_index(name, new_index)
        return new_index

    def connect(self):
        """
        Create a new connection object to communicate with the database.
        """
        self._temp_indexes = {}
        return self._connect()

    # ---- Temp indexes
    def temp_indexes(self, name):
        """
        Return a list of temporary indexes that were requested by the manager,
        but but haven't been commited yet to the database.
        """
        return self._temp_indexes.get(name, [])

    def add_temp_index(self, name, index):
        """
        Add index to the list of temporary indexes for the data related
        to name.
        """
        self._temp_indexes[name] = self._temp_indexes.get(name, []) + [index]

    def del_temp_index(self, name, index):
        """
        Remove index from the list of temporary indexes for the data related
        to name.
        """
        if name in self._temp_indexes:
            try:
                self._temp_indexes[name].remove(index)
            except ValueError:
                pass


class DatabaseAccessor(DatabaseAccessorBase):
    """
    Sardes database accessor class.

    All database accessors *must* inherit this class and reimplement
    its interface.
    """

    # ---- Database connection
    @abstractmethod
    def is_connected(self):
        """
        Return whether a connection to the database is currently active or not.

        Returns
        -------
        bool
            Whether a connection to the database is currently active or not.
        """
        pass

    @abstractmethod
    def _connect(self):
        """
        Create a new connection object to communicate with the database.
        """
        pass

    @abstractmethod
    def close_connection(self):
        """
        Close the currently active connection with the database.
        """
        pass

    # --- Indexes
    def _create_index(self, name):
        """
        Return a new index that can be used subsequently to add a new item
        related to name in the database.

        Note that you need to take into account temporary indexes that might
        have been requested by the database manager but haven't been
        commited yet to the database.
        """
        raise NotImplementedError

    # ---- Observation Wells
    def get_observation_wells_statistics(self):
        """
        Return a :class:`pandas.DataFrame` containing statistics related to
        the water level data acquired in the observation wells of the
        monitoring network.

        Returns
        -------
        :class:`pandas.DataFrame`
            A :class:`pandas.DataFrame` containing statistics related to
            the water level data acquired in the observation wells of the
            monitoring network.

            The row indexes of the dataframe must correspond to the
            observation well IDs, which are unique identifiers used to
            reference the wells in the database.

            The dataframe can contain any of the following optinal columns.

            Optional Columns
            ~~~~~~~~~~~~~~~~
            - first_date: datetime
                The date of the first water level measurements made in each
                observation well.
            - last_date: datetime
                The date of the last water level measurements made in each
                observation well.
            - mean_water_level: float
                The average water level value calculated over the whole
                monitoring period for each well.
        """
        raise NotImplementedError

    def add_observation_wells_data(self, sampling_feature_id,
                                   attribute_values):
        """
        Add a new observation well to the database using the provided
        sampling feature ID and attribute values.

        Parameters
        ----------
        sampling_feature_id: int, :class:`uuid.UUID`
            A unique identifier used to reference the observation well
            in the database.
        attribute_values: dict
            A dictionary containing the attribute values for the new
            observation well.
        """
        raise NotImplementedError

    def set_observation_wells_data(self, sampling_feature_id, attribute_name,
                                   value):
        """
        Save in the database the new attribute value for the observation well
        corresponding to the specified sampling feature ID.

        Parameters
        ----------
        sampling_feature_id: int, :class:`uuid.UUID`
            A unique identifier used to reference the observation well
            in the database.
        attribute_name: str
            Name of the attribute of the observation well for which the
            value need to be updated in the database.
            See :func:`get_observation_wells_data` for the list of attributes
            that are defined for the observation well feature.
        value: object
            Value that need to be updated for the corresponding attribute and
            observation well.
        """
        raise NotImplementedError

    def get_observation_wells_data(self):
        """
        Return a :class:`pandas.DataFrame` containing the information related
        to the observation wells that are saved in the database.

        Returns
        -------
        :class:`pandas.DataFrame`
            A :class:`pandas.DataFrame` containing the information related
            to the observation wells that are saved in the database.

            The row indexes of the dataframe must correspond to the
            observation well IDs, which are unique identifiers used to
            reference the wells in the database.

            The dataframe must contain at least the required columns and any
            of the optional columns that are listed below.

            Required Columns
            ~~~~~~~~~~~~~~~~
            - obs_well_id: str
                The unique identifier of the observation well.
            - latitude: float
                The latitude of the observation well location in decimal
                degrees.
            - longitude: float
                The longitude of the observation well location in decimal
                degrees.

            Optional Columns
            ~~~~~~~~~~~~~~~~
            - common_name: str
                The human readable name of the well.
            - municipality: str
                The municipality where the well is installed.
            - aquifer_type: str
                Indicates if the well is open in the bedrock or in the
                unconsolidated sediment.
            - confinement: str
                Indicates if the confinement at the well location is confined,
                unconfined or semi-confined,
            - aquifer_code: int
                A code that represents the combination of aquifer type and
                confinement for the well.
            - in_recharge_zone: bool
                Indicates whether the observation well is located in or in
                the proximity a recharge zone.
            - is_influenced: bool
                Indicates whether the water levels measured in that well are
                influenced or not by anthropic phenomenon.
            - elevation: float
                The elevation of the ground surface at the observation well
                location in meters above sea level.
            - is_station_active: bool
                Indicates whether the station is still active or not.
            - obs_well_notes: str
                Any notes related to the observation well.
        """
        raise NotImplementedError

    # ---- Repere
    def add_repere_data(self, repere_id, attribute_values):
        """
        Add a new observation well repere data to the database using the
        provided repere ID and attribute values.

        Parameters
        ----------
        repere_id: int, :class:`uuid.UUID`
            A unique identifier used to reference the observation well
            repere data in the database.
        attribute_values: dict
            A dictionary containing the attribute values for the new
            observation well repere data.
        """
        raise NotImplementedError

    def set_repere_data(self, repere_id, attribute_name, attribute_value):
        """
        Save in the database the new attribute value for the observation well
        repere data corresponding to the specified ID.

        Parameters
        ----------
        repere_id: int, :class:`uuid.UUID`
            A unique identifier used to reference the observation well
            repere data in the database.
        attribute_name: str
            Name of the attribute of the observation well repere data for
            which the value need to be updated in the database.
        value: object
            Value that need to be updated for the corresponding attribute and
            repere data.
        """
        raise NotImplementedError

    def get_repere_data(self):
        """
        Return a :class:`pandas.DataFrame` containing the information related
        to observation wells repere data.

        Returns
        -------
        :class:`pandas.DataFrame`
            A :class:`pandas.DataFrame` containing the information related
            to observation wells repere data.

            The row indexes of the dataframe must correspond to the IDs
            used to reference the repere data in the database.

            The dataframe can contain any of the columns that are listed below.

            Columns
            ~~~~~~~~~~~~~~~~
            - sampling_feature_uuid: int, :class:`uuid.UUID`
                A unique identifier that is used to reference the observation
                well for which the repere data are associated.
            - top_casing_alt: float
                The altitude values given in meters of the top of the
                observation wells' casing.
            - casing_length: str
                The lenght of the casing above ground level given in meters.
            - start_date: datetime
                The date and time after which repere data are valid.
            - end_date: datetime
                The date and time before which repere data are valid.
            - is_alt_geodesic: bool
                Whether the top_casing_alt value is geodesic.
            - repere_note: bool
                Any note related to the repere data.
        """
        raise NotImplementedError

    # ---- Sonde Brands and Models Library
    def get_sonde_models_lib(self):
        """
        Return a :class:`pandas.DataFrame` containing the information related
        to sonde brands and models.

        Returns
        -------
        :class:`pandas.DataFrame`
            A :class:`pandas.DataFrame` containing the information related
            to sonde brands and models.

            The row indexes of the dataframe must correspond to the IDs
            used to reference the sonde model and brand combination in
            the database.

            The dataframe can contain any of the columns that are
            listed below.

            Columns
            ~~~~~~~~~~~~~~~~
            - sonde_brand_model: str
                A sonde brand and model combination.
            - sonde_brand: str
                A sonde manufacturer.
            - sonde_model: str
                A sonde model.
        """
        raise NotImplementedError

    # ---- Sondes Inventory
    def add_sondes_data(self, sonde_id, attribute_values):
        """
        Add a new sonde to the database using the provided sonde ID
        and attribute values.

        Parameters
        ----------
        sonde_id: int, :class:`uuid.UUID`
            A unique identifier used to reference the sonde in the database.
        attribute_values: dict
            A dictionary containing the attribute values for the new sonde.
        """
        raise NotImplementedError

    def get_sondes_data(self):
        """
        Return a :class:`pandas.DataFrame` containing the information related
        to the sondes used to monitor groundwater properties in the wells.

        Returns
        -------
        :class:`pandas.DataFrame`
            A :class:`pandas.DataFrame` containing the information related
            to the sondes used to monitor groundwater properties in the wells.

            The row indexes of the dataframe must correspond to the
            sonde IDs, which are unique identifiers used to reference the
            sondes in the database.

            The dataframe can contain any of the columns that are
            listed below.

            Required Columns
            ~~~~~~~~~~~~~~~~
            - sonde_serial_no: str
                The serial number of the sonde.
            - sonde_model_id: int, :class:`uuid.UUID`
                The ID used to reference the sonde brand and model in the
                database.
            - date_reception: datetime
                The date when the sonde was added to the inventory.
            - date_withdrawal: datetime
                The date when the sonde was removed from the inventory.
            - in_repair: bool
                Indicate wheter the sonde is currently being repaired.
            - out_of_order: bool
                Indicate whether the sonde is out of order.
                unconsolidated sediment.
            - lost: bool
                Indicates whether the sonde has been lost.
            - off_network: bool
                Indicate whether the sonde is currently being used outside
                of the monitoring network.
            - sonde_notes: str
                Any notes related to the sonde.

            Optional Columns
            ~~~~~~~~~~~~~~~~
            - sonde_brand_model: str
                The brand and model of the sonde.
            - sonde_brand: str
                The brand of the sonde.
            - sonde_model: str
                The model of the sonde.
        """
        raise NotImplementedError

    def set_sondes_data(self, sonde_id, attribute_name, value):
        """
        Save in the database the new attribute value for the sonde
        corresponding to the specified sonde UID.

        Parameters
        ----------
        sonde_id: int, :class:`uuid.UUID`
            A unique identifier used to reference the sonde in the database.
        attribute_name: str
            Name of the attribute of the sonde for which the
            value need to be updated in the database.
            See :func:`get_sondes_data` for the list of attributes
            that are defined for the sonde feature.
        value: object
            Value that need to be updated for the corresponding attribute and
            sonde.
        """
        raise NotImplementedError

    # ---- Sonde installations
    def add_sonde_installations(self, installation_id, attribute_values):
        """
        Add a new sonde installation to the database using the provided ID
        and attribute values.

        Parameters
        ----------
        installation_id: int, :class:`uuid.UUID`
            A unique identifier used to reference the sonde installation
            in the database.
        attribute_values: dict
            A dictionary containing the attribute values for the new
            sonde installation.
        """
        raise NotImplementedError

    def set_sonde_installations(self, installation_id, attribute_name, value):
        """
        Save in the database the new attribute value for the sonde
        installation corresponding to the specified id.

        Parameters
        ----------
        installation_id: int, :class:`uuid.UUID`
            A unique identifier used to reference the sonde installation
            in the database.
        attribute_name: str
            Name of the attribute of the sonde installation for which the
            value need to be updated in the database.
        value: object
            Value that need to be updated for the corresponding attribute and
            sonde installation id.
        """
        raise NotImplementedError

    def get_sonde_installations(self):
        """
        Return a :class:`pandas.DataFrame` containing information related to
        sonde installations made in the observation wells of the monitoring
        network.

        Returns
        -------
        :class:`pandas.DataFrame`
            A :class:`pandas.DataFrame` containing information related to
            sonde installations made in the observation wells of the monitoring
            network.

            The row indexes of the dataframe must correspond to the
            IDs used to reference each installation in the database.

            The dataframe must contain the following columns.

            Required Columns
            ~~~~~~~~~~~~~~~~
            - sampling_feature_uuid: object
                A unique identifier that is used to reference the observation
                well in which the sonde are installed.
            - sonde_uuid: object
                A unique identifier used to reference each sonde in the
                database.
            - start_date: datetime
                The date and time at which the sonde was installed in the well.
            - end_date: datetime
                The date and time at which the sonde was removed from the well.
            - install_depth: float
                The depth at which the sonde was installed in the well.
        """
        raise NotImplementedError

    # ---- Timeseries
    def get_timeseries_for_obs_well(self, obs_well_id, data_type):
        """
        Return a :class:`TimeSeriesGroup` containing the :class:`TimeSeries`
        holding the data acquired in the observation well for the
        specified monitored property.

        Parameters
        ----------
        obs_well_id: object
            A unique identifier that is used to reference the observation well
            in the database.
        data_type: :class:`sardes.api.timeseries.DataType`
            The type of time data that we want to extract from the database.

        Returns
        -------
        :class:`TimeSeriesGroup`
            A :class:`TimeSeriesGroup` containing the :class:`TimeSeries`
            holding the data acquired in the observation well for the
            specified monitored property.
        """
        raise NotImplementedError

    # ---- Manual Measurements
    def add_manual_measurements(self, measurement_id, attribute_values):
        """
        Add a new manual measurement to the database using the provided ID
        and attribute values.

        Parameters
        ----------
        measurement_id: int, :class:`uuid.UUID`
            A unique identifier used to reference the manual measurement
            in the database.
        attribute_values: dict
            A dictionary containing the attribute values for the new
            manual measurement.
        """
        raise NotImplementedError

    def get_manual_measurements(self):
        """
        Return a :class:`pandas.DataFrame` containing the water level manual
        measurements made in the observation wells for the entire monitoring
        network.

        Returns
        -------
        :class:`pandas.DataFrame`
            A :class:`pandas.DataFrame` containing the information related
            to the observation wells that are saved in the database.

            The row indexes of the dataframe must correspond to the
            IDs used to reference each manual measurement in the database.

            The dataframe must contain the following columns.

            Required Columns
            ~~~~~~~~~~~~~~~~
            - sampling_feature_uuid: object
                A unique identifier that is used to reference the observation
                well in the database in which the manual measurement was made.
            - datetime: :class:`datetime.Datetime`
                A datetime object corresponding to the date and time when the
                manual measurement was made in the well.
            - value: float
                The value of the water level that was measured manually
                in the well.
            - notes: str
                Any notes related to the manual measurement.
        """
        raise NotImplementedError

    def set_manual_measurements(self, measurement_id, attribute_name, value):
        """
        Save in the database the new attribute value for the manual
        measurement  corresponding to the specified id.

        Parameters
        ----------
        measurement_id: int, :class:`uuid.UUID`
            A unique identifier used to reference the manual measurement
            in the database.
        attribute_name: str
            Name of the attribute of the manual measurement for which the
            value need to be updated in the database.
        value: object
            Value that need to be updated for the corresponding attribute and
            manual measurement id.
        """
        raise NotImplementedError
