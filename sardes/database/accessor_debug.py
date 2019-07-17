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

# ---- Third party imports
import pandas as pd

# ---- Local imports
from sardes.database.accessor_base import DatabaseAccessorBase


OBS_WELLS_DATA = {}
for i in range(5):
    OBS_WELLS_DATA['obs_well_id'] = 'obs_well_id #{}'.format(i)
    OBS_WELLS_DATA['common_name'] = 'common_name #{}'.format(i)
    OBS_WELLS_DATA['municipality'] = 'municipality #{}'.format(i)
    OBS_WELLS_DATA['aquifer_type'] = 'aquifer #{}'.format(i)
    OBS_WELLS_DATA['confinement'] = 'confinement #{}'.format(i)
    OBS_WELLS_DATA['aquifer_code'] = i
    OBS_WELLS_DATA['in_recharge_zone'] = 'zone_rechar #{}'.format(i)
    OBS_WELLS_DATA['is_influenced'] = 'influences #{}'.format(i)
    OBS_WELLS_DATA['latitude'] = 45 + i / 10
    OBS_WELLS_DATA['longitude'] = -75 + i / 10
    OBS_WELLS_DATA['is_station_active'] = 'station_active #{}'.format(i)
    OBS_WELLS_DATA['obs_well_notes'] = 'note #{}'.format(i)
OBS_WELLS_DF = pd.DataFrame(OBS_WELLS_DATA, range(5))


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
        self._wells = deepcopy(OBS_WELLS_DF)

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


if __name__ == '__main__':
    accessor = DatabaseAccessorDebug()
    accessor.connect()
    obs_wells = accessor.get_observation_wells()
