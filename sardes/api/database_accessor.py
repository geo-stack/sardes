# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

from __future__ import annotations

# ---- Standard imports
from abc import ABC, abstractmethod

# ---- Third party imports
import pandas as pd
from pandas import Series, DataFrame
from pandas.api.types import is_list_like


class DatabaseAccessorError(Exception):
    """The basic Exception class for Sardes database accessor."""

    def __init__(self, accessor, message):
        super().__init__(
            "{} ERROR: {}".format(accessor.__class__.__name__, message)
            )


class DatabaseAccessorBase(ABC):
    """
    Basic functionality for Sardes database accessor.

    WARNING: Don't override any methods or attributes present here unless you
    know what you are doing.
    """

    def __init__(self):
        self._connection = None
        self._connection_error = None

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

    def set(self, name: str, index: object,
            values: dict, auto_commit: bool = True) -> None:
        """
        Set in the database the values related to the specified name
        and index.
        """
        getattr(self, 'set_' + name)(index, values)
        if auto_commit:
            self.commit()

    def add(self, name: str,
            values: dict | list[dict],
            auto_commit: bool = True) -> list:
        """
        Add a new item to the data related to name in the database using
        the given primary_key and values.
        """
        is_dict = isinstance(values, dict)
        values = [values] if is_dict else list(values)
        indexes = getattr(self, '_add_' + name)(values)
        if auto_commit:
            self.commit()
        return indexes[0] if is_dict else indexes

    def delete(self, name: str,
               indexes: list,
               auto_commit: bool = True) -> None:
        """
        Delete from the database the items related to name at the
        specified indexes.
        """
        indexes = [indexes, ] if not is_list_like(indexes) else list(indexes)
        getattr(self, '_del_' + name)(indexes)
        if auto_commit:
            self.commit()

    def connect(self):
        """
        Create a new connection object to communicate with the database.
        """
        self._connection, self._connection_error = self._connect()


class DatabaseAccessor(DatabaseAccessorBase):
    """
    Sardes database accessor class.

    All database accessors *must* inherit this class and reimplement
    its interface.
    """

    # ---- Database connection
    @abstractmethod
    def commit(self):
        "Commit transaction to the database"
        pass

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

    # ---- Observation Wells
    def get_observation_wells_data_overview(self):
        """
        Return a :class:`pandas.DataFrame` containing an overview of
        the water level data that are available for each observation well
        of the monitoring network.

        Returns
        -------
        :class:`pandas.DataFrame`
            A :class:`pandas.DataFrame` containing an overview of
            the water level data that are available for each observation well
            of the monitoring network.

            The row indexes of the dataframe must correspond to the
            observation well IDs, which are unique identifiers used to
            reference the wells in the database.

            The dataframe can contain any of the following optional columns.

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

    @abstractmethod
    def _add_observation_wells_data(
            self, attribute_values: list[dict]) -> list:
        """
        Add a list of new observation wells to the database.

        Note:
            This method should not be called directly. Please use instead the
            public method `add`.

        Parameters
        ----------
        attribute_values: list[dict]
            A list of dictionaries containing the attribute values for the new
            observation wells to be added to the database.

        Returns
        -------
        list
            The list of indexes that are used to reference the new observation
            wells that were added to the database.
        """
        pass

    def set_observation_wells_data(self, sampling_feature_id,
                                   attribute_values):
        """
        Save in the database new attribute values for the observation well
        corresponding to the specified sampling feature ID.

        Parameters
        ----------
        sampling_feature_id: int, :class:`uuid.UUID`
            A unique identifier used to reference the observation well
            in the database.
        attribute_values: dict
            A dictionary containing the attribute values that need to be
            changed in the database for the corresponding sampling_feature_id.
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
            - in_recharge_zone: str
                Indicates whether the observation well is located in or in
                the proximity a recharge zone.
            - is_influenced: str
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

    @abstractmethod
    def _del_observation_wells_data(self, indexes: list):
        """
        Delete the observation wells corresponding to the specified indexes.

        Note:
            This method should not be called directly. Please use instead the
            public method `delete`.
        """
        pass

    # ---- Repere
    @abstractmethod
    def _add_repere_data(self, attribute_values: list[dict]) -> list:
        """
        Add a list of repere to the database.

        Note:
            This method should not be called directly. Please use instead the
            public method `add`.

        Parameters
        ----------
        attribute_values: list[dict]
            A list of dictionaries containing the attribute values for the new
            repere to be added to the database.

        Returns
        -------
        list
            The list of indexes that are used to reference the new repere
            that were added to the database.
        """
        pass

    def set_repere_data(self, repere_id, attribute_values):
        """
        Save in the database the new attribute values for the repere data
        corresponding to the specified repere_id.

        Parameters
        ----------
        repere_id: object
            A unique identifier used to reference the repere data for wich
            attribute values need to be changed in the database.
        attribute_values: dict
            A dictionary containing the attribute values that need to be
            changed in the database for the corresponding repere_id.
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

    @abstractmethod
    def _del_repere_data(self, indexes: list):
        """
        Delete the repere data corresponding to the specified indexes.

        Note:
            This method should not be called directly. Please use instead the
            public method `delete`.
        """
        pass

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

    def set_sonde_models_lib(self, sonde_model_id, attribute_values,
                             auto_commit=True):
        """
        Save in the database the new attribute values for the sonde model
        corresponding to the specified sonde_model_id.

        Parameters
        ----------
        sonde_model_id: object
            A unique identifier used to reference the sonde model for wich
            attribute values need to be changed in the database.
        attribute_values: dict
            A dictionary containing the attribute values that need to be
            changed in the database for the corresponding sonde_model_id.
        """
        raise NotImplementedError

    @abstractmethod
    def _add_sonde_models_lib(self, attribute_values: list[dict]) -> list:
        """
        Add a list of sonde models to the database.

        Note:
            This method should not be called directly. Please use instead the
            public method `add`.

        Parameters
        ----------
        attribute_values: list[dict]
            A list of dictionaries containing the attribute values for the new
            sonde models to be added to the database.

        Returns
        -------
        list
            The list of indexes that are used to reference the new sonde
            models that were added to the database.
        """
        pass

    @abstractmethod
    def _del_sonde_models_lib(self, indexes: list):
        """
        Delete the sonde models corresponding to the specified indexes.

        Note:
            This method should not be called directly. Please use instead the
            public method `delete`.
        """
        pass

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

    def set_sondes_data(self, sonde_id, attribute_values):
        """
        Save in the database the new attribute value for the sonde
        corresponding to the specified sonde_id.

        Parameters
        ----------
        sonde_id: int, :class:`uuid.UUID`
            A unique identifier used to reference the sonde in the database.
        attribute_values: dict
            A dictionary containing the attribute values that need to be
            changed in the database for the corresponding sonde_id.
        """
        raise NotImplementedError

    @abstractmethod
    def _del_sondes_data(self, indexes: list):
        """
        Delete the sondes data corresponding to the specified indexes.

        Note:
            This method should not be called directly. Please use instead the
            public method `delete`.
        """
        pass

    # ---- Sonde installations
    def add_sonde_installations(self, installation_id, attribute_values):
        """
        Add a new sonde installation to the database using the provided
        installation_id and attribute values.

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

    def set_sonde_installations(self, installation_id, attribute_values):
        """
        Save in the database the new attribute values for the sonde
        installation corresponding to the specified installation_id.

        Parameters
        ----------
        installation_id: object
            A unique identifier used to reference the sonde installation
            for wich attribute values need to be changed in the database.
        attribute_values: dict
            A dictionary containing the attribute values that need to be
            changed in the database for the corresponding installation_id.
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

    @abstractmethod
    def _del_sonde_installations(self, indexes: list):
        """
        Delete the sonde installations corresponding to the specified indexes.

        Note:
            This method should not be called directly. Please use instead the
            public method `delete`.
        """
        pass

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

            Required elements
            ~~~~~~~~~~~~~~~~~
            - datetime :class:`datetime.Datetime`
                A datetime object corresponding to the date and time when the
                manual measurement was made in the well.
            - value: float
                The numerical value of the water level that was
                measured manually in the well.
            - sampling_feature_uuid: object
                The unique identifier that is used to reference the observation
                well in which the manual measurement was made.

            Optional elements
            ~~~~~~~~~~~~~~~~~
            - notes: str
                A note related to the manual measurement.
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

    def set_manual_measurements(self, measurement_id, attribute_values):
        """
        Save in the database the new attribute values for the
        measurement corresponding to the specified measurement_id.

        Parameters
        ----------
        measurement_id: int, :class:`uuid.UUID`
            A unique identifier used to reference the manual measurement
            in the database.
        attribute_values: dict
            A dictionary containing the attribute values that need to be
            changed in the database for the corresponding measurement_id.
        """
        raise NotImplementedError

    @abstractmethod
    def _del_manual_measurements(self, indexes: list):
        """
        Delete the manual measurements corresponding to the specified indexes.

        Note:
            This method should not be called directly. Please use instead the
            public method `delete`.
        """
        pass

    # ---- Timeseries
    def get_timeseries_for_obs_well(self, obs_well_id, data_types=None):
        """
        Return a pandas dataframe containing the readings for the given
        data types and monitoring station.

        If no data type are specified, then return the entire dataset for
        the specified monitoring station.

        Parameters
        ----------
        obs_well_id: object
            A unique identifier that is used to reference the observation well
            in the database.
        data_type: list of str or list of DataType
            A list of timeseries data types that we want to extract
            from the database.

        Returns
        -------
        tseries_dataf: pandas.DataFrame
            A pandas dataframe containing the readings for the given
            data types and obervation well.
            Time must be saved as datetime in a column named 'datetime'.
            The columns in which the numerical values are stored must be a
            member of :class:`sardes.api.timeseries.DataType`.
            Finally, the observation ID and a sonde serial number must be
            provided for each value and stored in columns named, respectively,
            'obs_id' and 'sonde_id'.
        """
        raise NotImplementedError

    def save_timeseries_data_edits(self, tseries_edits):
        """
        Save in the database a set of edits that were made to to timeseries
        data that were already saved in the database.

        Parameters
        ----------
        tseries_edits: pandas.DataFrame
            A multi-indexes pandas dataframe that contains the edited
            numerical values that need to be saved in the database.
            The indexes of the dataframe correspond, respectively, to the
            datetime (datetime), observation ID (str) and the data type
            (DataType) corresponding to the edited value.
        """
        raise NotImplementedError

    def add_timeseries_data(self, tseries_data, obs_well_uuid,
                            sonde_installation_uuid=None):
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
        obs_well_id: int, :class:`uuid.UUID`
            A unique identifier that is used to reference in the database
            the observation well in which the data were measured.
        installation_id: int, :class:`uuid.UUID`
            A unique identifier used to reference the sonde installation, if
            any, corresponding to the current set of data.
        """
        raise NotImplementedError

    def delete_timeseries_data(self, tseries_dels):
        """
        Delete data in the database for the observation IDs, datetime and
        data type specified in tseries_dels.

        Parameters
        ----------
        tseries_dels: pandas.DataFrame
            A pandas dataframe that contains the observation IDs, datetime,
            and data_type for which timeseries data need to be deleted
            from the database.
        """
        raise NotImplementedError
