# -*- coding: utf-8 -*-
"""
Created on Thu Dec 23 10:57:02 2021

@author: User
"""
import os.path as osp
import os
import uuid
import pandas as pd
import numpy as np
from sardes.database.accessors import DatabaseAccessorSardesLite
from sardes.api.timeseries import DataType
from time import perf_counter

# Prepare the database
database = osp.join(osp.dirname(__file__), 'sqlite_database_test.db')
if osp.exists(database):
    os.remove(database)

ts = perf_counter()
dbaccessor = DatabaseAccessorSardesLite(database)
dbaccessor.init_database()
dbaccessor.connect()
print("Init database: {:0.3f}".format(perf_counter() - ts))

sampling_feature_uuid = uuid.uuid4()

# Prepare the timeseries data.
new_tseries_data = pd.DataFrame(
    [], columns=['datetime', DataType.WaterLevel, DataType.WaterTemp])
new_tseries_data['datetime'] = pd.date_range(
    start='1/1/1960', end='1/1/2020')
new_tseries_data[DataType.WaterLevel] = np.random.rand(
    len(new_tseries_data))
new_tseries_data[DataType.WaterTemp] = np.random.rand(
    len(new_tseries_data))
assert len(new_tseries_data) == 21916

# Add timeseries data to the database.
ts = perf_counter()
dbaccessor.add_timeseries_data(
    new_tseries_data, sampling_feature_uuid, None)

wlevel_data = dbaccessor.get_timeseries_for_obs_well(
    sampling_feature_uuid, DataType.WaterLevel)
assert len(wlevel_data) == 21916

wtemp_data = dbaccessor.get_timeseries_for_obs_well(
    sampling_feature_uuid, DataType.WaterTemp)
assert len(wtemp_data) == 21916
print("Add readings data: {:0.3f}".format(perf_counter() - ts))

# Delete all timeseries data from the database.
ts = perf_counter()
wlevel_data['data_type'] = DataType.WaterLevel
wtemp_data['data_type'] = DataType.WaterTemp
tseries_dels = pd.concat((
    wlevel_data[['datetime', 'obs_id', 'data_type']],
    wtemp_data[['datetime', 'obs_id', 'data_type']]
    ))
dbaccessor.delete_timeseries_data(tseries_dels)
print("Delete readings data: {:0.3f}".format(perf_counter() - ts))

wlevel_data = dbaccessor.get_timeseries_for_obs_well(
    sampling_feature_uuid, DataType.WaterLevel)
assert len(wlevel_data) == 0

wtemp_data = dbaccessor.get_timeseries_for_obs_well(
    sampling_feature_uuid, DataType.WaterTemp)
assert len(wtemp_data) == 0

dbaccessor.close_connection()
if osp.exists(database):
    os.remove(database)
