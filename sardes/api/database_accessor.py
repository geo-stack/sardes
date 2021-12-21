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
from typing import Any
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
    def get(self, name: str):
        """
        Get the data related to name from the database.
        """
        return getattr(self, '_get_' + name)()

    def set(self, name: str, index: Any,
            values: dict, auto_commit: bool = True) -> None:
        """
        Set in the database the values related to the specified name
        and index.
        """
        getattr(self, '_set_' + name)(index, values)
        if auto_commit:
            self.commit()

    def add(self, name: str, values: list[dict] = None,
            indexes: list[Any] = None, auto_commit: bool = True) -> list:
        """
        Add a new item to the data related to name in the database using
        the given primary_key and values.
        """
        if values is None:
            if not is_list_like(indexes):
                values = {}
            else:
                values = [{}] * len(indexes)
        is_single = isinstance(values, dict)

        values = [values, ] if is_single else list(values)
        if indexes is not None:
            indexes = [indexes, ] if is_single else list(indexes)

        indexes = getattr(self, '_add_' + name)(values, indexes)
        if auto_commit:
            self.commit()

        return indexes[0] if is_single else indexes

    def delete(self, name: str, indexes: list[Any],
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

    # ---- Observation Wells Interface
    # =========================================================================
    # Note: The methods in this section should not be called directly. Please
    #       use instead the public methods "add", "get", "delete", and "set".
    # =========================================================================
    @abstractmethod
    def _get_observation_wells_data(self):
        """
        Return the information related to the observation wells that are
        saved in the database.

        Returns
        -------
        :class:`pandas.DataFrame`
            A pandas dataframe containing information related to the
            observation wells that are saved in the database.

            The index of the dataframe must contain the indexes or keys that
            are used to reference the observation wells in the database.

            See :data:`DATABASE_CONCEPTUAL_MODEL` for a detailed
            description of the content and structure that the dataframe
            returned by this method should follow.
        """
        pass

    @abstractmethod
    def _add_observation_wells_data(
            self, values: list[dict], indexes: list = None) -> list:
        """
        Add a list of new observation wells to the database.

        Parameters
        ----------
        values: list[dict]
            A list of dictionaries containing the attribute values for the new
            observation wells to be added to the database.

            See :data:`DATABASE_CONCEPTUAL_MODEL` for a detailed
            description of the content and structure that each
            dictionary must follow.
        indexes: list, optional
            A list of indexes to use when adding the new observation wells
            to the database.

        Returns
        -------
        list
            The list of indexes that are used to reference the new observation
            wells that were added to the database.
        """
        pass

    @abstractmethod
    def _set_observation_wells_data(self, index: Any, values: dict):
        """
        Set in the database the values of the observation well data
        corresponding to the specified index.

        Parameters
        ----------
        index: Any
            A unique identifier used to reference the observation well
            in the database.
        values: dict
            A dictionary containing the attribute values of the observation
            well that needs to be updated in the database for the specified
            index.

            See :data:`DATABASE_CONCEPTUAL_MODEL` for a detailed
            description of the attributes and data types that the dictionary
            can contained.
        """
        pass

    @abstractmethod
    def _del_observation_wells_data(self, indexes: list):
        """
        Delete the observation wells corresponding to the specified indexes.
        """
        pass

    # ---- Repere Data Interface
    # =========================================================================
    # Note: The methods in this section should not be called directly. Please
    #       use instead the public methods "add", "get", "delete", and "set".
    # =========================================================================
    @abstractmethod
    def _get_repere_data(self):
        """
        Return the information related to the repere data of the
        observation wells.

        Returns
        -------
        :class:`pandas.DataFrame`
            A pandas dataframe containing information related to the
            observation wells repere data that are saved in the database.

            The index of the dataframe must contain the indexes or keys that
            are used to reference the repere data in the database.

            See :data:`DATABASE_CONCEPTUAL_MODEL` for a detailed
            description of the content and structure that the dataframe
            returned by this method should follow.
        """
        pass

    @abstractmethod
    def _add_repere_data(
            self, values: list[dict], indexes: list = None) -> list:
        """
        Add a list of repere to the database.

        Parameters
        ----------
        values: list[dict]
            A list of dictionaries containing the attribute values for the new
            repere to be added to the database.

            See :data:`DATABASE_CONCEPTUAL_MODEL` for a detailed
            description of the content and structure that each
            dictionary must follow.
        indexes: list, optional
            A list of indexes to use when adding the new repere
            to the database.

        Returns
        -------
        list
            The list of indexes that are used to reference the new repere
            that were added to the database.
        """
        pass

    @abstractmethod
    def _set_repere_data(self, index: Any, values: dict):
        """
        Set in the database the values of the repere data
        corresponding to the specified index.

        Parameters
        ----------
        index: Any
            A unique identifier used to reference the repere data
            in the database.
        values: dict
            A dictionary containing the attribute values of the repere data
            that needs to be updated in the database for the specified index.

            See :data:`DATABASE_CONCEPTUAL_MODEL` for a detailed
            description of the attributes and data types that the dictionary
            can contained.
        """
        pass

    @abstractmethod
    def _del_repere_data(self, indexes: list):
        """
        Delete the repere data corresponding to the specified indexes.
        """
        pass

    # ---- Sonde Models Interface
    # =========================================================================
    # Note: The methods in this section should not be called directly. Please
    #       use instead the public methods "add", "get", "delete", and "set".
    # =========================================================================
    @abstractmethod
    def _get_sonde_models_lib(self):
        """
        Return a :class:`pandas.DataFrame` containing the information related
        to sonde brands and models.

        Returns
        -------
        :class:`pandas.DataFrame`
            A pandas dataframe containing information related to existing
            sonde models that are saved in the database.

            The index of the dataframe must contain the indexes or keys that
            are used to reference the sonde models in the database.

            See :data:`DATABASE_CONCEPTUAL_MODEL` for a detailed
            description of the content and structure that the dataframe
            returned by this method should follow.
        """
        pass

    @abstractmethod
    def _add_sonde_models_lib(
            self, values: list[dict], indexes: list = None) -> list:
        """
        Add a list of sonde models to the database.

        Parameters
        ----------
        values: list[dict]
            A list of dictionaries containing the attribute values for the new
            sonde models to be added to the database.

            See :data:`DATABASE_CONCEPTUAL_MODEL` for a detailed
            description of the content and structure that each
            dictionary must follow.
        indexes: list, optional
            A list of indexes to use when adding the new sonde models
            to the database.

        Returns
        -------
        list
            The list of indexes that are used to reference the new sonde
            models that were added to the database.
        """
        pass

    @abstractmethod
    def _set_sonde_models_lib(self, index: Any, values: dict):
        """
        Set in the database the values of the sonde model
        corresponding to the specified index.

        Parameters
        ----------
        index: Any
            A unique identifier used to reference the sonde model
            in the database.
        values: dict
            A dictionary containing the attribute values of the sonde model
            that needs to be updated in the database for the specified index.

            See :data:`DATABASE_CONCEPTUAL_MODEL` for a detailed
            description of the attributes and data types that the dictionary
            can contained.
        """
        pass

    @abstractmethod
    def _del_sonde_models_lib(self, indexes: list):
        """
        Delete the sonde models corresponding to the specified indexes.
        """
        pass

    # ---- Sondes Inventory Interface
    @abstractmethod
    def _add_sondes_data(
            self, values: list[dict], indexes: list = None) -> list:
        """
        Add a list of new sondes to the database.

        Parameters
        ----------
        values: list[dict]
            A list of dictionaries containing the attribute values for the new
            sondes to be added to the database.

            See :data:`DATABASE_CONCEPTUAL_MODEL` for a detailed
            description of the content and structure that each
            dictionary must follow.
        indexes: list, optional
            A list of indexes to use when adding the new sondes
            to the database.

        Returns
        -------
        list
            The list of indexes that are used to reference the new sondes
            that were added to the database.
        """
        pass

    def get_sondes_data(self):
        """
        Return a :class:`pandas.DataFrame` containing the information related
        to the sondes used to monitor groundwater properties in the wells.

        Returns
        -------
        :class:`pandas.DataFrame`
            A pandas dataframe containing information related to the
            sondes used to monitor groundwater properties in the wells.

            The index of the dataframe must contain the indexes or keys that
            are used to reference the sondes in the database.

            See :data:`DATABASE_CONCEPTUAL_MODEL` for a detailed
            description of the content and structure that the dataframe
            returned by this method should follow.
        """
        raise NotImplementedError

    @abstractmethod
    def _set_sondes_data(self, index: Any, values: dict):
        """
        Set in the database the values of the sondes data
        corresponding to the specified index.

        Parameters
        ----------
        index: Any
            A unique identifier used to reference the sondes data
            in the database.
        values: dict
            A dictionary containing the attribute values of the sondes data
            that needs to be updated in the database for the specified index.

            See :data:`DATABASE_CONCEPTUAL_MODEL` for a detailed
            description of the attributes and data types that the dictionary
            can contained.
        """
        pass

    @abstractmethod
    def _del_sondes_data(self, indexes: list):
        """
        Delete the sondes data corresponding to the specified indexes.
        """
        pass

    # ---- Sonde Installations Interface
    # =========================================================================
    # Note: The methods in this section should not be called directly. Please
    #       use instead the public methods "add", "get", "delete", and "set".
    # =========================================================================
    def _add_sonde_installations(
            self, values: list[dict], indexes: list = None) -> list:
        """
        Add a list of sonde installations to the database.

        Parameters
        ----------
        values: list[dict]
            A list of dictionaries containing the attribute values for the new
            sonde installations to be added to the database.

            See :data:`DATABASE_CONCEPTUAL_MODEL` for a detailed
            description of the content and structure that each
            dictionary must follow.
        indexes: list, optional
            A list of indexes to use when adding the new sonde installations
            to the database.

        Returns
        -------
        list
            The list of indexes that are used to reference the new sonde
            installations that were added to the database.
        """
        pass

    @abstractmethod
    def _set_sonde_installations(self, index: Any, values: dict):
        """
        Set in the database the values of the sonde installation
        corresponding to the specified index.

        Parameters
        ----------
        index: Any
            A unique identifier used to reference the sonde installation
            in the database.
        values: dict
            A dictionary containing the attribute values of the sonde
            installation that needs to be updated in the database for
            the specified index.

            See :data:`DATABASE_CONCEPTUAL_MODEL` for a detailed
            description of the attributes and data types that the dictionary
            can contained.
        """
        pass

    def get_sonde_installations(self):
        """
        Return the information related to the installations of the sondes in
        the wells.

        Returns
        -------
        :class:`pandas.DataFrame`
            A pandas dataframe containing information related to the
            installations of the sonde in the wells.

            The index of the dataframe must contain the indexes or keys that
            are used to reference the sonde installations in the database.

            See :data:`DATABASE_CONCEPTUAL_MODEL` for a detailed
            description of the content and structure that the dataframe
            returned by this method should follow.
        """
        raise NotImplementedError

    @abstractmethod
    def _del_sonde_installations(self, indexes: list):
        """
        Delete the sonde installations corresponding to the specified indexes.
        """
        pass

    # ---- Manual Measurements Interface
    # =========================================================================
    # Note: The methods in this section should not be called directly. Please
    #       use instead the public methods "add", "get", "delete", and "set".
    # =========================================================================
    def _add_manual_measurements(
            self, values: list[dict], indexes: list = None) -> list:
        """
        Add a list of manual measurements to the database.

        Parameters
        ----------
        values: list[dict]
            A list of dictionaries containing the attribute values for the new
            manual measurements to be added to the database.

            See :data:`DATABASE_CONCEPTUAL_MODEL` for a detailed
            description of the content and structure that each
            dictionary must follow.
        indexes: list, optional
            A list of indexes to use when adding the manual measurements
            to the database.

        Returns
        -------
        list
            The list of indexes that are used to reference the new
            manual measurements that were added to the database.
        """
        pass

    def get_manual_measurements(self):
        """
        Return the water level manual measurements that are saved in
        the database.

        Returns
        -------
        :class:`pandas.DataFrame`
            A pandas dataframe containing the manual measurements of the
            water level that are saved in the database.

            The index of the dataframe must contain the indexes or keys that
            are used to reference the manual measurements in the database.

            See :data:`DATABASE_CONCEPTUAL_MODEL` for a detailed
            description of the content and structure that the dataframe
            returned by this method should follow.
        """
        raise NotImplementedError

    @abstractmethod
    def _set_manual_measurements(self, index: Any, values: dict):
        """
        Set in the database the values of the manual measurement
        corresponding to the specified index.

        Parameters
        ----------
        index: Any
            A unique identifier used to reference the manual measurement
            in the database.
        values: dict
            A dictionary containing the attribute values of the manual
            measurement that needs to be updated in the database for
            the specified index.

            See :data:`DATABASE_CONCEPTUAL_MODEL` for a detailed
            description of the attributes and data types that the dictionary
            can contained.
        """
        pass

    @abstractmethod
    def _del_manual_measurements(self, indexes: list):
        """
        Delete the manual measurements corresponding to the specified indexes.
        """
        pass

    # ---- Timeseries Interface
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
