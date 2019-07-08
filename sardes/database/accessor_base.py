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
from time import sleep


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

