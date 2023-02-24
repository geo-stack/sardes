# -*- coding: utf-8 -*-
"""
Created on Fri Feb 24 11:54:12 2023
@author: User
"""

import pandas as pd
from sardes.database.accessors.accessor_sardes_lite import (
    DatabaseAccessorSardesLite)

database = ("D:/Desktop/rsesq_prod_sample.db")
dbaccessor = DatabaseAccessorSardesLite(database)


obs_wells = dbaccessor.get('observation_wells_data')
sonde_data = dbaccessor.get('sondes_data')
sonde_models_lib = dbaccessor.get('sonde_models_lib')
sonde_installations = dbaccessor.get('sonde_installations')
repere_data = dbaccessor.get('repere_data')

# %% Delete monitoring data.

for obs_well_id in obs_wells['obs_well_id']:
    if obs_well_id in ['01030001', '01070001', '01070002', '13000001']:
        continue
    print(f'Deleting monitoring data for station {obs_well_id}')

    sampling_feature_uuid = (
        dbaccessor._get_sampling_feature_uuid_from_name(obs_well_id))

    readings = dbaccessor.get_timeseries_for_obs_well(sampling_feature_uuid)
    tseries_dels = readings.drop(['install_depth', 'sonde_id'], axis=1)
    tseries_dels = tseries_dels.set_index(['datetime', 'obs_id'], drop=True)
    tseries_dels = tseries_dels.stack().reset_index()
    tseries_dels = tseries_dels.drop([0], axis=1)
    tseries_dels = tseries_dels.rename(columns={'level_2': 'data_type'})

    dbaccessor._delete_timeseries_data(tseries_dels)
    dbaccessor._session.commit()

dbaccessor.execute('vacuum')

# %%

for obs_well_id in obs_wells['obs_well_id']:
    if obs_well_id in ['01030001', '01070001', '01070002', '13000001']:
        continue
    print(f'Deleting station {obs_well_id}')

    sampling_feature_uuid = (
        dbaccessor._get_sampling_feature_uuid_from_name(obs_well_id))

    try:
        dbaccessor._del_observation_wells_data([sampling_feature_uuid])
    except Exception:
        pass
dbaccessor._session.commit()

# %% Delete faulty observations

sampling_feature_uuids = []
for obs_well_id in obs_wells['obs_well_id']:
    if obs_well_id not in ['01030001', '01070001', '01070002', '13000001']:
        sampling_feature_uuids.append(
            dbaccessor._get_sampling_feature_uuid_from_name(obs_well_id)
            )

observation_data = dbaccessor._get_observation_data()
mask = observation_data['sampling_feature_uuid'].isin(sampling_feature_uuids)
faulty_obs_data = observation_data[mask]

for obs_id in faulty_obs_data.index:
    observation = dbaccessor._get_observation(obs_id)
    dbaccessor._session.delete(observation)
dbaccessor._session.commit()

# %% Delete sonde features.

sonde_installations = dbaccessor.get('sonde_installations')
sonde_data = dbaccessor.get('sondes_data')
for sonde_id in sonde_data.index:
    if sonde_id in sonde_installations['sonde_uuid'].values:
        continue
    dbaccessor._del_sondes_data([sonde_id])
dbaccessor._session.commit()
dbaccessor.execute('vacuum')
