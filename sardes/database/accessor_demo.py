# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Accessor implementation of a Demo database.
"""

# ---- Standard imports
import datetime as dt
from time import sleep

# ---- Third party imports
import numpy as np
import pandas as pd
from pandas import Series

# ---- Local imports
from sardes.api.database_accessor import DatabaseAccessor
from sardes.api.timeseries import TimeSeriesGroup, TimeSeries


# =============================================================================
# Module variable definition
# =============================================================================
OBS_WELLS_DATA = []
OBS_WELL_ID = ['0343128', '0466773', '0622056', '0652184', '0702303']
for i in range(5):
    AQUIFER_CODE = str(int(np.random.rand(1) * 5))
    AQUIFER_CONFINEMENT, AQUIFER_TYPE = [
        ('Confined', 'Rock'),
        ('Confined', 'Sediments'),
        ('Semi-Confined', 'Rock'),
        ('Semi-Confined', 'Sediments'),
        ('Unconfined', 'Rock'),
        ('Unconfined', 'Sediments')][int(AQUIFER_CODE)]
    OBS_WELLS_DATA.append([
        OBS_WELL_ID[i],
        'PO{:01d}'.format(i + 1),
        'Municipality {:01d}'.format(i + 1),
        AQUIFER_TYPE,
        AQUIFER_CONFINEMENT,
        AQUIFER_CODE,
        str(bool(np.floor(np.random.rand(1) * 2))),
        str(bool(np.floor(np.random.rand(1) * 2))),
        round(45 + np.random.rand(1)[0] * 2, 6),
        round(-75 + np.random.rand(1)[0] * 2, 6),
        bool(np.floor(np.random.rand(1) * 2)),
        'Notes for observation well #{}'.format(OBS_WELL_ID)])
OBS_WELLS_DF = pd.DataFrame(
    OBS_WELLS_DATA,
    columns=['obs_well_id', 'common_name', 'municipality',
             'aquifer_type', 'confinement', 'aquifer_code',
             'in_recharge_zone', 'is_influenced', 'latitude',
             'longitude', 'is_station_active', 'obs_well_notes']
    )

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

MANUAL_MEASUREMENTS = pd.DataFrame([
    [OBS_WELLS_DF.index[0], dt.datetime(2010, 8, 10, 16, 10, 34), 5.23],
    [OBS_WELLS_DF.index[0], dt.datetime(2010, 11, 10, 12, 55, 22), 4.36],
    [OBS_WELLS_DF.index[0], dt.datetime(2011, 8, 2, 18, 50, 17), 4.91],
    [OBS_WELLS_DF.index[1], dt.datetime(2009, 8, 2, 18, 34, 38), 28.34],
    [OBS_WELLS_DF.index[2], dt.datetime(2015, 8, 2, 18, 37, 23), 14.87],
    [OBS_WELLS_DF.index[2], dt.datetime(2016, 2, 4, 13, 26, 3), 2.03]
    ],
    columns=['sampling_feature_uuid', 'datetime', 'manual_measurement']
    )

SONDE_MODELS_LIB = pd.DataFrame([
    ['Solinst', 'Barologger M1.5 Gold'],
    ['Solinst', 'LT M10 Gold'],
    ['Solinst', 'LT M10 Edge'],
    ['Solinst', 'Barologger M1,5'],
    ['Solinst', 'LT M20 Gold'],
    ['Solinst', 'L M10'],
    ['Telog 1', 'Druck'],
    ['Telog 2', 'Druck'],
    ['In-Situ', 'Troll']],
    columns=['sonde_brand', 'sonde_model']
    )

SONDES_DATA = pd.DataFrame([
    [0, 'Solinst Barologger M1.5 Gold', '1022034',
     dt.date(2007, 3, 26), dt.date(2017, 11, 27),
     False, True, True, False,
     'Notes for sonde Solinst Barologger M1.5 Gold 1022034'],
    [1, 'Solinst LT M10 Gold', '1062392',
     dt.date(2011, 5, 10), dt.date(2017, 11, 27),
     False, True, True, False,
     'Notes for sonde Solinst LT M10 Gold 1062392'],
    [2, 'Solinst LT M10 Edge', '2004771',
     dt.date(2012, 1, 1), None,
     False, False, False, False,
     'Notes for sonde Solinst LT M10 Edge 2004771']],
    columns=['sonde_model_id', 'sonde_brand_model', 'sonde_serial_no',
             'date_reception', 'date_withdrawal', 'in_repair',
             'out_of_order', 'lost', 'off_network', 'sonde_notes']
    )


# =============================================================================
# Database accessor implementation
# =============================================================================
class DatabaseAccessorDemo(DatabaseAccessor):
    """
    Sardes accessor test and debug class.

    This accessor is for testing and debuging purposes and does not depend
    on a database.
    """

    def __init__(self, *args, **kargs):
        super().__init__()

    def is_connected(self):
        """
        Return whether a connection to a database is currently active or not.
        """
        return self._connection is not None

    def connect(self):
        """
        Create a new connection object to communicate with the database.
        """
        sleep(1)
        self._connection = True

    def close_connection(self):
        """
        Close the currently active connection with the database.
        """
        self._connection = None

    # ---- Observation Wells
    @property
    def observation_wells(self):
    def add_observation_wells_data(self, sampling_feature_id,
                                   attribute_values):
        """
        Return the list of observation wells that are saved in the
        database.
        Add a new observation well to the database using the provided
        sampling feature ID and attribute values.
        """
        return OBS_WELLS_DF['obs_well_id'].values
        for column in OBS_WELLS_DF.columns:
            OBS_WELLS_DF.loc[sampling_feature_id, column] = (
                attribute_values.get(column, None))

    def set_observation_wells_data(self, sampling_feature_id, attribute_name,
                                   attribute_value):
        """
        Save in the database the new attribute value for the observation well
        corresponding to the specified sampling feature ID.
        """
        OBS_WELLS_DF.loc[sampling_feature_id, attribute_name] = attribute_value

    def get_observation_wells_data(self):
        """
        Return a :class:`pandas.DataFrame` containing the information related
        to the observation wells that are saved in the database.
        """
        sleep(0.3)
        df = OBS_WELLS_DF.copy()

        # Save the dtype of the indexes and the name of the table.
        df.index_dtype = type(OBS_WELLS_DF.index[0]).__name__
        df.name = 'observation_wells_data'
        return df

    # ---- Sonde Brands and Models Library
    def get_sonde_models_lib(self):
        """
        Return a :class:`pandas.DataFrame` containing the information related
        to sonde brands and models.
        """
        sleep(0.1)
        df = SONDE_MODELS_LIB.copy()

        # Combine the brand and model into a same field.
        df['sonde_brand_model'] = (
            df[['sonde_brand', 'sonde_model']]
            .apply(lambda x: ' '.join(x), axis=1))
        df = df.sort_values('sonde_brand_model')

        # Save the dtype of the indexes and the name of the table.
        df.index_dtype = type(SONDE_MODELS_LIB.index[0]).__name__
        df.name = 'sonde_models_lib'
        return df

    # ---- Sondes Inventory
    def get_sondes_data(self):
        """
        Return a :class:`pandas.DataFrame` containing the information related
        to the sondes used to monitor groundwater properties in the wells.
        """
        sleep(0.3)
        df = (SONDES_DATA
              .copy()
              .sort_values(['sonde_brand_model', 'sonde_serial_no'])
              .drop('sonde_brand_model', axis=1))

        # Save the dtype of the indexes and the name of the table.
        df.index_dtype = type(SONDES_DATA.index[0]).__name__
        df.name = 'sondes_data'
        return df

    def set_sondes_data(self, sonde_id, attribute_name, attribute_value):
        """
        Save in the database the new attribute value for the sonde
        corresponding to the specified sonde UID.
        """
        SONDES_DATA.loc[sonde_id, attribute_name] = attribute_value

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

    # ---- Manual mesurements
    def get_manual_measurements(self):
        """
        Return a :class:`pandas.DataFrame` containing the water level manual
        measurements made in the observation wells for the entire monitoring
        network.
        """
        sleep(0.1)
        df = MANUAL_MEASUREMENTS.copy()

        # Save the dtype of the indexes and the name of the table.
        df.index_dtype = type(MANUAL_MEASUREMENTS.index[0]).__name__
        df.name = 'manual_measurements'
        return df


if __name__ == '__main__':
    accessor = DatabaseAccessorDemo()
    accessor.connect()
    obs_wells = accessor.get_observation_wells_data()
    wlevel = accessor.get_timeseries_for_obs_well('dfsdf', 'NIV_EAU')
    print(wlevel[0])
    print(accessor.observation_wells)
    print(accessor.monitored_properties)
