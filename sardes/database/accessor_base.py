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


class ObservationWell(object):
    """
    Sardes observation well class.
    """
    __attrs__ = ['no_well', 'common_name', 'municipality', 'aquifer_type',
                 'aquifer_code', 'confinement', 'in_recharge_zone',
                 'is_influenced', 'latitude', 'longitude', 'elevation',
                 'is_station_active', 'note']

    def __init__(self, no_well: str, common_name: str = None,
                 municipality: str = None, aquifer_type: str = None,
                 aquifer_code: int = None, confinement: str = None,
                 in_recharge_zone: bool = None, is_influenced: bool = None,
                 latitude: float = None, longitude: float = None,
                 elevation: float = None, is_station_active: bool = None,
                 note: str = None):
        self.no_well = no_well
        self.common_name = common_name
        self.municipality = municipality
        self.aquifer_type = aquifer_type
        self.aquifer_code = aquifer_code
        self.confinement = confinement
        self.in_recharge_zone = in_recharge_zone
        self.is_influenced = is_influenced
        self.latitude = latitude
        self.longitude = longitude
        self.elevation = elevation
        self.is_station_active = is_station_active
        self.note = note

    def __eq__(self, other):
        if not isinstance(other, ObservationWell):
            # Don't attempt to compare against unrelated types
            return NotImplemented
        try:
            return all([getattr(self, attr) == getattr(other, attr) for
                        attr in self.__attrs__])
        except AttributeError:
            return False


class DatabaseAccessorBase(ABC):
    """
    Sardes accessor class.

    All accessors *must* inherit this class and reimplement its interface.
    """

    def __init__(self, *args, **kargs):
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

    def get_observation_wells(self, sort=True):
        """
        Get a list of ObservationWell objects containing information
        related to the observation wells that are saved in the database.

        Returns
        -------
        list
            A list of ObservationWell objects containing information
            related to the observation wells that are saved in the database.
        """
        return []
