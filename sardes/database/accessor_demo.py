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
from random import randrange
import datetime as dt
from time import sleep

# ---- Third party imports
import numpy as np
import pandas as pd
from pandas import Series

# ---- Local imports
from sardes.api.database_accessor import DatabaseAccessor
from sardes.api.timeseries import DataType, TimeSeriesGroup, TimeSeries


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

DATE_RANGE = pd.date_range(start='1/1/2015', end='1/1/2019')
NYEAR = DATE_RANGE[-1].year - DATE_RANGE[0].year + 1
YEARLY_RADS = np.linspace(0, 2 * NYEAR * np.pi, len(DATE_RANGE))

TSERIES = {}
TSERIES_VALUES = 25 * np.sin(YEARLY_RADS) + 5
TSERIES_VALUES += 3 * np.random.rand(len(TSERIES_VALUES))
TSERIES[DataType.WaterTemp] = Series(TSERIES_VALUES, index=DATE_RANGE)

TSERIES_VALUES = np.hstack((np.linspace(100, 95, len(YEARLY_RADS) // 2),
                            np.linspace(95, 98, len(YEARLY_RADS) // 2)))
TSERIES_VALUES += 1 * np.sin(YEARLY_RADS)
TSERIES_VALUES += 2 * np.sin(YEARLY_RADS * 2)
TSERIES_VALUES += 1 * np.sin(YEARLY_RADS * 4)
TSERIES_VALUES += 0.5 * np.sin(YEARLY_RADS * 8)
TSERIES_VALUES += 0.25 * np.random.rand(len(TSERIES_VALUES))
TSERIES[DataType.WaterLevel] = Series(TSERIES_VALUES, index=DATE_RANGE)

MANUAL_MEASUREMENTS = pd.DataFrame([
    [OBS_WELLS_DF.index[0], dt.datetime(2010, 8, 10, 16, 10, 34), 5.23, ''],
    [OBS_WELLS_DF.index[0], dt.datetime(2010, 11, 10, 12, 55, 22), 4.36, ''],
    [OBS_WELLS_DF.index[0], dt.datetime(2011, 8, 2, 18, 50, 17), 4.91, ''],
    [OBS_WELLS_DF.index[1], dt.datetime(2009, 8, 2, 18, 34, 38), 28.34, ''],
    [OBS_WELLS_DF.index[2], dt.datetime(2015, 8, 2, 18, 37, 23), 14.87, ''],
    [OBS_WELLS_DF.index[2], dt.datetime(2016, 2, 4, 13, 26, 3), 2.03, '']
    ],
    columns=['sampling_feature_uuid', 'datetime', 'value', 'notes']
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
    [SONDE_MODELS_LIB.index[0], 'Solinst Barologger M1.5 Gold', '1022034',
     dt.date(2007, 3, 26), dt.date(2017, 11, 27),
     False, True, True, False,
     'Notes for sonde Solinst Barologger M1.5 Gold 1022034'],
    [SONDE_MODELS_LIB.index[1], 'Solinst LT M10 Gold', '1016042',
     dt.date(2011, 5, 10), dt.date(2017, 11, 27),
     False, True, True, False,
     'Notes for sonde Solinst LT M10 Gold 1016042'],
    [SONDE_MODELS_LIB.index[2], 'Solinst LT M10 Edge', '2004771',
     dt.date(2012, 1, 1), None,
     False, False, False, False,
     'Notes for sonde Solinst LT M10 Edge 2004771']],
    columns=['sonde_model_id', 'sonde_brand_model', 'sonde_serial_no',
             'date_reception', 'date_withdrawal', 'in_repair',
             'out_of_order', 'lost', 'off_network', 'sonde_notes']
    )

SONDE_INSTALLATIONS = pd.DataFrame([
    [dt.datetime(2015, 7, 27, 23, 0), None, 1,
     OBS_WELLS_DF.index[0], SONDES_DATA.index[0]],
    [dt.datetime(2015, 7, 27, 23, 0), None, 9.82,
     OBS_WELLS_DF.index[0], SONDES_DATA.index[1]],
    [dt.datetime(2016, 3, 4, 12, 0), dt.datetime(2019, 3, 4, 12, 0), 9.82,
     OBS_WELLS_DF.index[1], SONDES_DATA.index[2]]],
    columns=['start_date', 'end_date', 'install_depth',
             'sampling_feature_uuid', 'sonde_uuid']
    )

REPERE_DATA = []
for i in range(len(OBS_WELLS_DF)):
    REPERE_DATA.append([
        OBS_WELLS_DF.index[i],
        randrange(99999) / 100,
        randrange(20, 200) / 100,
        dt.datetime(randrange(2000, 2006), randrange(12) + 1,
                    randrange(28) + 1, randrange(23) + 1),
        None,
        bool(randrange(2)),
        'Note #{}'.format(i)
        ])
REPERE = pd.DataFrame(
    REPERE_DATA,
    columns=['sampling_feature_uuid', 'top_casing_alt', 'casing_length',
             'start_date', 'end_date', 'is_alt_geodesic', 'repere_note'])


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

    def _connect(self):
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

    # --- Indexes
    def _create_index(self, name):
        """
        Return a new index that can be used subsequently to add a new item
        related to name in the database.

        Note that you need to take into account temporary indexes that might
        have been requested by the database manager but haven't been
        commited yet to the database.
        """
        if name == 'observation_wells_data':
            max_commited_id = max(OBS_WELLS_DF.index)
        elif name == 'sondes_data':
            max_commited_id = max(SONDES_DATA.index)
        elif name == 'manual_measurements':
            max_commited_id = max(MANUAL_MEASUREMENTS.index)
        else:
            raise NotImplementedError
        return max(self.temp_indexes(name) + [max_commited_id]) + 1

    # ---- Observation Wells
    def get_observation_wells_statistics(self):
        """
        Return a :class:`pandas.DataFrame` containing statistics related to
        the water level data acquired in the observation wells of the
        monitoring network.
        """
        obs_well_stats = pd.DataFrame([], index=OBS_WELLS_DF.index)
        obs_well_stats['first_date'] = np.min(
            TSERIES[DataType.WaterLevel].index)
        obs_well_stats['last_date'] = np.max(
            TSERIES[DataType.WaterLevel].index)
        obs_well_stats['mean_water_level'] = np.mean(
            TSERIES[DataType.WaterLevel])
        return obs_well_stats

    def add_observation_wells_data(self, sampling_feature_id,
                                   attribute_values):
        """
        Add a new observation well to the database using the provided
        sampling feature ID and attribute values.
        """
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

        return df

    # ---- Repere
    def add_repere_data(self, repere_id, attribute_values):
        """
        Add a new observation well repere data to the database using the
        provided repere ID and attribute values.
        """
        for column in REPERE.columns:
            REPERE.loc[repere_id, column] = attribute_values.get(column, None)

    def set_repere_data(self, repere_id, attribute_name, attribute_value):
        """
        Save in the database the new attribute value for the observation well
        repere data corresponding to the specified ID.
        """
        REPERE.loc[repere_id, attribute_name] = attribute_value

    def get_repere_data(self):
        """
        Return a :class:`pandas.DataFrame` containing the information related
        to observation wells repere data.
        """
        sleep(0.3)
        return REPERE.copy()

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

        return df

    # ---- Sondes Inventory
    def add_sondes_data(self, sonde_id, attribute_values):
        """
        Add a new sonde to the database using the provided sonde ID
        and attribute values.
        """
        for column in SONDES_DATA.columns:
            SONDES_DATA.loc[sonde_id, column] = (
                attribute_values.get(column, None))

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

        return df

    def set_sondes_data(self, sonde_id, attribute_name, attribute_value):
        """
        Save in the database the new attribute value for the sonde
        corresponding to the specified sonde UID.
        """
        SONDES_DATA.loc[sonde_id, attribute_name] = attribute_value

    # ---- Sonde installations
    def add_sonde_installations(self, install_id, attr_values):
        """
        Add a new sonde installation to the database using the provided ID
        and attribute values.
        """
        for column in SONDE_INSTALLATIONS.columns:
            SONDE_INSTALLATIONS.loc[install_id, column] = (
                attr_values.get(column, None))

    def set_sonde_installations(self, install_id, attr_name, attr_value,
                                auto_commit=True):
        """
        Save in the database the new attribute value for the sonde
        installation corresponding to the specified id.
        """
        SONDE_INSTALLATIONS.loc[install_id, attr_name] = attr_value

    def get_sonde_installations(self):
        """
        Return a :class:`pandas.DataFrame` containing information related to
        sonde installations made in the observation wells of the monitoring
        network.
        """
        sleep(0.3)
        return SONDE_INSTALLATIONS.copy()

    # ---- Monitored properties
    def get_timeseries_for_obs_well(self, obs_well_id, data_type):
        """
        Return a :class:`MonitoredProperty` object containing the
        :class:`TimeSeries` objects holding the data acquired in the
        observation well for the specified monitored property.
        """
        data_type = DataType(data_type)
        if data_type in TSERIES:
            data_units = {
                DataType.WaterEC: "",
                DataType.WaterLevel: "m",
                DataType.WaterTemp: "\u00B0C"}[data_type]
            tseries_group = TimeSeriesGroup(
                data_type, data_type.label, data_units)
            tseries_group.add_timeseries(TimeSeries(
                TSERIES[data_type],
                tseries_id="CHANNEL_UUID",
                tseries_name=data_type.label,
                tseries_units=data_units,
                tseries_color=data_type.color
                ))
            return tseries_group
        else:
            return None

    # ---- Manual mesurements
    def add_manual_measurements(self, measurement_id, attribute_values):
        """
        Add a new manual measurements to the database using the provided ID
        and attribute values.
        """
        for column in MANUAL_MEASUREMENTS.columns:
            MANUAL_MEASUREMENTS.loc[measurement_id, column] = (
                attribute_values.get(column, None))

    def get_manual_measurements(self):
        """
        Return a :class:`pandas.DataFrame` containing the water level manual
        measurements made in the observation wells for the entire monitoring
        network.
        """
        sleep(0.1)
        df = MANUAL_MEASUREMENTS.copy()

        return df

    def set_manual_measurements(self, measurement_id, attribute_name,
                                attribute_value):
        """
        Save in the database the new attribute value for the manual
        measurement corresponding to the specified id.
        """
        MANUAL_MEASUREMENTS.loc[
            measurement_id, attribute_name] = attribute_value


if __name__ == '__main__':
    accessor = DatabaseAccessorDemo()
    accessor.connect()
    obs_wells = accessor.get_observation_wells_data()
    wlevel = accessor.get_timeseries_for_obs_well('', DataType.WaterLevel)
    obs_well_stats = accessor.get_observation_wells_statistics()
    print(wlevel)
