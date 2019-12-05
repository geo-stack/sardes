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

    def get(self, name, *args, **kargs):
        """
        Get the data related to name from the database.
        """
        method_to_exec = getattr(self, 'get_' + name)
        return method_to_exec(*args, **kargs)

    def set(self, name, *args, **kargs):
        """
        Save the data related to name in the database.
        """
        getattr(self, 'set_' + name)(*args, **kargs)


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
    def connect(self):
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

    # ---- Observation Wells
    @property
    @abstractmethod
    def observation_wells(self):
        """
        Return the list of observation wells that are saved in the
        database.

        Returns
        -------
        list of str
            A list of strings corresponding to the name given to the
            observation wells that are saved in the database.
        """
        pass

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

    # ---- Monitored properties
    @property
    @abstractmethod
    def monitored_properties(self):
        """
        Returns the list of properties for which time data is stored in the
        database.

        Returns
        -------
        list of str
            A list of strings corresponding to the properties for which time
            data is stored in the database.
        """
        pass

    @abstractmethod
    def get_monitored_property_name(self, monitored_property):
        """
        Return the common human readable name for the corresponding
        monitored property.

        Returns
        -------
        str
            A string corresponding to the common human readable name used to
            reference this monitored property in the GUI and the graphs.
        """
        pass

    @abstractmethod
    def get_monitored_property_units(self, monitored_property):
        """
        Return the units in which the time data for this monitored property
        are saved in the database.

        Returns
        -------
        str
            A string corresponding to the units in which the time data for
            this monitored property are saved in the database.
        """
        pass

    # ---- Timeseries
    @abstractmethod
    def get_timeseries_for_obs_well(self, obs_well_id, monitored_property):
        """
        Return a :class:`TimeSeriesGroup` containing the :class:`TimeSeries`
        holding the data acquired in the observation well for the
        specified monitored property.

        Parameters
        ----------
        obs_well_id: object
            A unique identifier that is used to reference the observation well
            in the database.
        monitored_property: object
            The identifier used to reference the property for which we want
            to extract the time data from the database.

        Returns
        -------
        :class:`TimeSeriesGroup`
            A :class:`TimeSeriesGroup` containing the :class:`TimeSeries`
            holding the data acquired in the observation well for the
            specified monitored property.
        """
        pass

    # ---- Manual Measurements
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
                well in the database.
            - datetime: :class:`datetime.Datetime`
                A datetime object corresponding to the time when the manual
                measurement was made in the well.
            - manual_measurement: float
                The value of the water level that was measured manually
                in the well.
        """
        raise NotImplementedError

    def set_manual_measurements(self, *args, **kargs):
        pass
