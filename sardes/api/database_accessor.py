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
import pandas as pd


class DatabaseAccessorBase(ABC):
    """
    Sardes database accessor class.

    All database accessors *must* inherit this class and reimplement
    its interface.
    """

    def __init__(self, *args, **kargs):
        self._connection = None
        self._connection_error = None

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

    def get_observation_wells(self):
        """
        Return a pandas DataFrame containing the information related
        to the observation wells that are saved in the database.

        Returns
        -------
        pandas.DataFrame
            A pandas DataFrame containing the information related
            to the observation wells that are saved in the database.

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
        return pd.DataFrame([])
