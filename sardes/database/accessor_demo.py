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
import numpy as np
import pandas as pd
from pandas import Series

# ---- Local imports
from sardes.api.database_accessor import DatabaseAccessorBase
from sardes.api.timeseries import TimeSeriesGroup, TimeSeries


# =============================================================================
# Module variable definition
# =============================================================================
OBS_WELLS_COLUMNS = ['obs_well_id', 'common_name', 'municipality',
                     'aquifer_type', 'confinement', 'aquifer_code',
                     'in_recharge_zone', 'is_influenced', 'latitude',
                     'longitude', 'is_station_active', 'obs_well_notes']

OBS_WELLS_DATA = []
for i in range(5):
    OBS_WELL_ID = '0'
    for _ in range(6):
        OBS_WELL_ID += str(int(np.random.rand(1) * 9))
    AQUIFER_CODE = int(np.random.rand(1) * 5)
    AQUIFER_TYPE, AQUIFER_CONFINEMENT = [
        ('Confined', 'Rock'),
        ('Confined', 'Sediments'),
        ('Semi-Confined', 'Rock'),
        ('Semi-Confined', 'Sediments'),
        ('Unconfined', 'Rock'),
        ('Unconfined', 'Sediments')][AQUIFER_CODE]

    OBS_WELLS_DATA.append([
        OBS_WELL_ID,
        'PO{:01d}'.format(i + 1),
        'Municipality {:01d}'.format(i + 1),
        AQUIFER_TYPE,
        AQUIFER_CONFINEMENT,
        AQUIFER_CODE,
        str(bool(np.floor(np.random.rand(1) * 2))),
        str(bool(np.floor(np.random.rand(1) * 2))),
        round(45 + np.random.rand(1)[0] * 2, 6),
        round(-75 + np.random.rand(1)[0] * 2, 6),
        str(bool(np.floor(np.random.rand(1) * 2))),
        'Notes for observation well #{}'.format(OBS_WELL_ID)])
OBS_WELLS_DF = pd.DataFrame(OBS_WELLS_DATA, columns=OBS_WELLS_COLUMNS)

MONITORED_PROPERTIES = ['NIV_EAU', 'TEMP', 'COND_ELEC']
MONITORED_PROPERTY_NAMES = {
    'COND_ELEC': "Water electrical conductivity",
    'NIV_EAU': "Water level",
    'TEMP': "Water level temperature"}
MONITORED_PROPERTY_UNITS = {
    'COND_ELEC': "",
    'NIV_EAU': "m",
    'TEMP': "\u00B0C"}

DATE_RANGE = pd.date_range(start='1/1/2015', end='1/1/2019')
NYEAR = DATE_RANGE[-1].year - DATE_RANGE[0].year + 1
YEARLY_RADS = np.linspace(0, 2 * NYEAR * np.pi, len(DATE_RANGE))

TSERIES = {}
TSERIES_VALUES = 25 * np.sin(YEARLY_RADS) + 5
TSERIES_VALUES += 3 * np.random.rand(len(TSERIES_VALUES))
TSERIES['TEMP'] = Series(TSERIES_VALUES, index=DATE_RANGE)

TSERIES_VALUES = np.hstack((np.linspace(100, 95, len(YEARLY_RADS) // 2),
                            np.linspace(95, 98, len(YEARLY_RADS) // 2)))
TSERIES_VALUES += 1 * np.sin(YEARLY_RADS)
TSERIES_VALUES += 2 * np.sin(YEARLY_RADS * 2)
TSERIES_VALUES += 1 * np.sin(YEARLY_RADS * 4)
TSERIES_VALUES += 0.5 * np.sin(YEARLY_RADS * 8)
TSERIES_VALUES += 0.25 * np.random.rand(len(TSERIES_VALUES))
TSERIES['NIV_EAU'] = Series(TSERIES_VALUES, index=DATE_RANGE)


# =============================================================================
# Database accessor implementation
# =============================================================================
class DatabaseAccessorDemo(DatabaseAccessorBase):
    """
    Sardes accessor test and debug class.

    This accessor is for testing and debuging purposes and does not depend
    on a database.
    """
    __database_type_name__ = 'Sardes Demo'

    def __init__(self, *args, **kargs):
        super().__init__()
        print("Instantiating DatabaseAccessorDemo with :")
        print("args :", args)
        print("kargs :", kargs)
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

    # ---- Observation wells
    @property
    def observation_wells(self):
        """
        Return the list of observation wells that are saved in the
        database.
        """
        return OBS_WELLS_DF['obs_well_id'].values

    def get_observation_wells_data(self):
        """
        Get a list of ObservationWell objects containing information related
        to the observation wells that are saved in the database.
        """
        print("Fetching observation wells from the database...", end='')
        sleep(0.5)
        print("done")
        return self._wells if self.is_connected() else []

    # ---- Monitored properties
    @property
    def monitored_properties(self):
        """
        Returns the list of properties for which time data is stored in the
        database.
        """
        return MONITORED_PROPERTIES

    def get_monitored_property_name(self, monitored_property):
        """
        Return the common human readable name for the corresponding
        monitored property.
        """
        return MONITORED_PROPERTY_NAMES[monitored_property]

    def get_monitored_property_units(self, monitored_property):
        """
        Return the units in which the time data for this monitored property
        are saved in the database.
        """
        return MONITORED_PROPERTY_UNITS[monitored_property]

    def get_monitored_property_color(self, monitored_property):
        return {'NIV_EAU': 'blue',
                'TEMP': 'red',
                'COND_ELEC': 'cyan'
                }[monitored_property]

    def get_timeseries_for_obs_well(self, obs_well_id, monitored_property):
        """
        Return a :class:`MonitoredProperty` object containing the
        :class:`TimeSeries` objects holding the data acquired in the
        observation well for the specified monitored property.
        """
        tseries_group = TimeSeriesGroup(
            monitored_property,
            self.get_monitored_property_name(monitored_property),
            self.get_monitored_property_units(monitored_property)
            )
        tseries_group.add_timeseries(TimeSeries(
            TSERIES[monitored_property],
            tseries_id="CHANNEL_UUID",
            tseries_name=(
                self.get_monitored_property_name(monitored_property)),
            tseries_units=(
                self.get_monitored_property_units(monitored_property)),
            tseries_color=(
                self.get_monitored_property_color(monitored_property))
            ))
        return tseries_group


if __name__ == '__main__':
    accessor = DatabaseAccessorDemo()
    accessor.connect()
    obs_wells = accessor.get_observation_wells_data()
    wlevel = accessor.get_timeseries_for_obs_well('dfsdf', 'NIV_EAU')
    print(wlevel[0])
    print(accessor.observation_wells)
    print(accessor.monitored_properties)
