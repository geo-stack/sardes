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
OBS_WELLS_DF = pd.DataFrame(
    [['03037041', "St-Paul-d'Abbotsford", "Saint-Paul-d'Abbotsford",
      'MT', 'Confined', 3, 'No', 'No', 45.445178, -72.828773, True, None],
     ['02200001', "Réserve de Duchénier", "Saint-Narcisse-de-Rimouski",
      'ROC', 'Unconfined', 2, 'Yes', 'No', 48.20282, -68.52795, True, None],
     ['02167001', 'Matane', 'Matane',
      'MT', 'Captive', 3, 'No', 'Yes', 48.81151, -67.53562, True, None],
     ['02600001', "L'Islet", "L'Islet",
      'ROC', 'Unconfined', 2, 'Yes', 'No', 47.093526, -70.338989, True, None],
     ['03040002', 'PO-01', 'Calixa-Lavallée',
      'ROC', 'Confined', 1, 'No', 'No', 45.74581, -73.28024, True, None]],
    columns=['obs_well_id', 'common_name', 'municipality',
             'aquifer_type', 'confinement', 'aquifer_code',
             'in_recharge_zone', 'is_influenced', 'latitude',
             'longitude', 'is_station_active', 'obs_well_notes']
    )

DATE_RANGE = pd.date_range(start='1/1/2014', end='31/12/2018')
NYEAR = DATE_RANGE[-1].year - DATE_RANGE[0].year + 1
YEARLY_RADS = np.array([i * (2 * np.pi) / 365.25 for
                        i in range(len(DATE_RANGE))])

OBSERVATIONS = pd.DataFrame(
    [],
    columns=['start_date', 'end_date',
             'obs_well_uuid', 'sonde_installation_uuid'])
TSERIES = {}
for obs_id, obs_well_id in enumerate(OBS_WELLS_DF.index):
    OBSERVATIONS = OBSERVATIONS.append(
        pd.DataFrame([[DATE_RANGE[0].to_pydatetime(),
                       DATE_RANGE[-1].to_pydatetime(),
                       obs_well_id, None]],
                     index=[obs_id],
                     columns=OBSERVATIONS.columns),
        ignore_index=False)

    TSERIES[obs_id] = {}

    # Generate water temperature synthetic data.
    # Note that we set the seed of the random number generator everytime
    # to make the random numbers predictables.
    np.random.seed(obs_id)
    WTEMP_TSERIES = 25 * np.cos(YEARLY_RADS + np.pi) + 5
    np.random.seed(obs_id)
    WTEMP_TSERIES += 3 * np.random.rand(len(WTEMP_TSERIES))
    TSERIES[obs_well_id][DataType.WaterTemp] = Series(
        WTEMP_TSERIES, index=DATE_RANGE)

    # Generate water level synthetic data.
    N = len(YEARLY_RADS)
    WLEVEL_TSERIES = np.array([3 + i * 1 / 365.25 for i in range(730)])
    WLEVEL_TSERIES = np.hstack([
        WLEVEL_TSERIES,
        np.array([WLEVEL_TSERIES[-1] - (i + 1) * 1 / 365.25
                  for i in range(N - 730)])
        ])
    WLEVEL_TSERIES += 0.25 * np.sin(YEARLY_RADS)
    WLEVEL_TSERIES += 0.5 * np.sin(YEARLY_RADS * 2)
    WLEVEL_TSERIES += 0.25 * np.sin(YEARLY_RADS * 4)
    WLEVEL_TSERIES += 0.25 * np.sin(YEARLY_RADS * 8)
    # We set the seed to make the random numbers predictables.
    np.random.seed(obs_id)
    WLEVEL_TSERIES += 0.1 * np.random.rand(len(WLEVEL_TSERIES))
    TSERIES[obs_id][DataType.WaterLevel] = Series(
        WLEVEL_TSERIES, index=DATE_RANGE)

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
    ['Solinst', 'Barologger M1.5'],
    ['Solinst', 'LT M10'],
    ['Solinst', 'LT M20 Gold'],
    ['Solinst', 'L M10'],
    ['Telog 1', 'Druck'],
    ['Telog 2', 'Druck'],
    ['In-Situ', 'Troll']],
    columns=['sonde_brand', 'sonde_model']
    )

SONDES_DATA = pd.DataFrame(
    [[SONDE_MODELS_LIB.index[1], 'Solinst LT M10 Gold', '1016042',
      dt.date(2006, 3, 30), pd.NaT,
      False, False, False, False, None],
     [SONDE_MODELS_LIB.index[1], 'Solinst LT M10 Gold', '1031928',
      dt.date(2008, 6, 4), pd.NaT,
      False, False, False, False, None],
     [SONDE_MODELS_LIB.index[1], 'Solinst LT M10 Gold', '1021777',
      dt.date(2007, 3, 26), pd.NaT,
      False, False, False, False, None],
     [SONDE_MODELS_LIB.index[0], 'Solinst Barologger M1.5 Gold', '1016387',
      dt.date(2006, 3, 30), pd.NaT,
      False, False, False, False, None],
     [SONDE_MODELS_LIB.index[3], 'Solinst Barologger M1.5', '2022144',
      dt.date(2013, 9, 1), pd.NaT,
      False, False, False, False, "Achetée par l'INRS"],
     [SONDE_MODELS_LIB.index[2], 'Solinst LT M10 Edge', '2007039',
      dt.date(2013, 9, 1), dt.date(2014, 6, 3),
      True, True, False, False, "Achetée par l'INRS"],
     [SONDE_MODELS_LIB.index[2], 'Solinst LT M10 Edge', '2006190',
      dt.date(2013, 9, 1), pd.NaT,
      False, False, False, False, "Achetée par l'INRS"],
     [SONDE_MODELS_LIB.index[4], 'Solinst LT M10', '1060487',
      dt.date(2012, 5, 5), pd.NaT,
      False, False, False, False, None],
     [SONDE_MODELS_LIB.index[0], 'Solinst Barologger M1.5 Gold', '1048409',
      dt.date(2010, 2, 8), pd.NaT,
      False, False, False, False, None],
     ],
    columns=['sonde_model_id', 'sonde_brand_model', 'sonde_serial_no',
             'date_reception', 'date_withdrawal', 'in_repair',
             'out_of_order', 'lost', 'off_network', 'sonde_notes']
    )

SONDE_INSTALLATIONS = pd.DataFrame(
    [[dt.datetime(2006, 8, 24, 18), pd.NaT, 9.02,
      OBS_WELLS_DF.index[0], SONDES_DATA.index[0]],
     [dt.datetime(2009, 7, 24, 19), pd.NaT, 7.19,
      OBS_WELLS_DF.index[1], SONDES_DATA.index[1]],
     [dt.datetime(2007, 11, 14, 19), pd.NaT, 10.1,
      OBS_WELLS_DF.index[2], SONDES_DATA.index[2]],
     [dt.datetime(2007, 11, 14, 19), pd.NaT, 2.0,
      OBS_WELLS_DF.index[2], SONDES_DATA.index[3]],
     [dt.datetime(2013, 10, 9, 1), pd.NaT, 1,
      OBS_WELLS_DF.index[3], SONDES_DATA.index[4]],
     [dt.datetime(2013, 10, 9, 1), dt.datetime(2014, 6, 3, 10), 8.16,
      OBS_WELLS_DF.index[3], SONDES_DATA.index[5]],
     [dt.datetime(2014, 6, 3, 10), pd.NaT, 8.16,
      OBS_WELLS_DF.index[3], SONDES_DATA.index[6]],
     [dt.datetime(2012, 5, 5, 19), pd.NaT, 9.24,
      OBS_WELLS_DF.index[4], SONDES_DATA.index[7]],
     [dt.datetime(2012, 5, 5, 19), pd.NaT, 1.0,
      OBS_WELLS_DF.index[4], SONDES_DATA.index[8]]
     ],
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
        stats_data = []
        for obs_well_id in OBS_WELLS_DF.index:
            stats_data.append([
                np.min(TSERIES[obs_well_id][DataType.WaterLevel].index),
                np.max(TSERIES[obs_well_id][DataType.WaterLevel].index),
                np.mean(TSERIES[obs_well_id][DataType.WaterLevel]),
                ])
        stats_df = pd.DataFrame(
            stats_data,
            columns=['first_date', 'last_date', 'mean_water_level'],
            index=OBS_WELLS_DF.index)
        return stats_df

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
        data_units = {
            DataType.WaterEC: "",
            DataType.WaterLevel: "m",
            DataType.WaterTemp: "\u00B0C"}[data_type]
        tseries_group = TimeSeriesGroup(
            data_type, data_type.title, data_units,
            yaxis_inverted=(data_type == DataType.WaterLevel))
        tseries_group.duplicated_data = []

        # Add timeseries data to the group.
        obs_ids = (OBSERVATIONS
                   [OBSERVATIONS['obs_well_uuid'] == obs_well_id]
                   .index)
        for obs_id in obs_ids:
            try:
                tseries_data = TSERIES[obs_id][DataType(data_type)]
            except KeyError:
                continue
            tseries_group.add_timeseries(TimeSeries(
                tseries_data,
                tseries_id=obs_id,
                tseries_name=data_type.title,
                tseries_units=data_units,
                tseries_color=data_type.color,
                sonde_id='1062392'
                ))
        return tseries_group

    def save_timeseries_data_edits(self, tseries_edits):
        """
        Save in the database a set of edits that were made to to timeseries
        data that were already saved in the database.
        """
        for (date_time, obs_id, data_type) in tseries_edits.index:
            value = tseries_edits.loc[(date_time, obs_id, data_type), 'value']
            TSERIES[obs_id][data_type].loc[date_time] = value

    def add_timeseries_data(self, tseries_data, obs_well_uuid,
                            sonde_installation_uuid=None):
        """
        Save in the database a set of timeseries data associated with the
        given well and sonde installation id.
        """
        sleep(0.5)
        new_obs_id = max(OBSERVATIONS.index) + 1
        OBSERVATIONS.loc[new_obs_id] = [
            min(tseries_data['datetime']),
            max(tseries_data['datetime']),
            obs_well_uuid,
            sonde_installation_uuid]

        TSERIES[new_obs_id] = {}
        for data_type in DataType:
            if data_type in tseries_data.columns:
                TSERIES[new_obs_id][data_type] = Series(
                    tseries_data[data_type],
                    index=tseries_data['datetime'])

    def delete_timeseries_data(self, tseries_dels):
        """
        Delete data in the database for the observation IDs, datetime and
        data type specified in tseries_dels.
        """
        for i in range(len(tseries_dels)):
            data = tseries_dels.iloc[i, ]
            TSERIES[data['obs_id']][data['data_type']].drop(
                data['datetime'], inplace=True)
        for obs_id in tseries_dels['obs_id'].unique():
            for tseries in TSERIES[obs_id].values():
                if len(tseries):
                    break
            else:
                print("Deleting observation {} because it is now empty."
                      .format(obs_id))
                del TSERIES[obs_id]

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
