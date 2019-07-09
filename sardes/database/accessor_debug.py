# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports
from time import sleep
from copy import deepcopy

# ---- Local imports
from sardes.database.accessor_base import DatabaseAccessorBase, ObservationWell


OBS_WELLS = [
    ObservationWell(
        no_well='no_well #{}'.format(i),
        common_name='common_name #{}'.format(i),
        municipality='municipality #{}'.format(i),
        aquifer_type='aquifer #{}'.format(i),
        confinement='confinement #{}'.format(i),
        aquifer_code=i,
        in_recharge_zone='zone_rechar #{}'.format(i),
        is_influenced='influences #{}'.format(i),
        latitude=45 + i / 10,
        longitude=-75 + i / 10,
        is_station_active='station_active #{}'.format(i),
        note='note #{}'.format(i)
        ) for i in range(5)]


class DatabaseAccessorDebug(DatabaseAccessorBase):
    """
    Sardes accessor test and debug class.

    This accessor is for testing and debuging purposes and does not depend
    on a database.
    """

    def __init__(self, *args, **kargs):
        super().__init__()
        print("Instantiating DatabaseAccessorDebug with :")
        print("args :", args)
        print("kargs :", kargs)
        self._connection = None
        self._connection_error = None
        self._wells = deepcopy(OBS_WELLS)

    def is_connected(self):
        """
        Return whether a connection to a database is currently active or not.
        """
        return self._connection is not None

    def connect(self):
        """
        Create a new connection object to communicate with the database.
        """
        print("Connecting to database...", end='')
        sleep(1)
        self._connection = True
        print("done")

    def close_connection(self):
        """
        Close the currently active connection with the database.
        """
        print("Closing connection to database...", end='')
        self._connection = None
        print("done")

    def get_observation_wells(self, sort=True):
        """
        Get a list of ObservationWell objects containing information related
        to the observation wells that are saved in the database.
        """
        print("Fetching observation wells from the database...", end='')
        sleep(0.5)
        print("done")
        return self._wells if self.is_connected() else []
