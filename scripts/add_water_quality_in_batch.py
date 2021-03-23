# -*- coding: utf-8 -*-
"""
Created on Tue Feb  2 13:53:30 2021
@author: User
"""
import os
import os.path as osp

from sardes.database.accessors.accessor_sardes_lite import (
    DatabaseAccessorSardesLite, CURRENT_SCHEMA_VERSION)


database = "D:/OneDrive/Sardes/rsesq_prod_02-04-2021.db"
accessor = DatabaseAccessorSardesLite(database)
if accessor.version() < CURRENT_SCHEMA_VERSION:
    accessor.init_database()

dirname = "D:/OneDrive/Sardes/Fichiers pour publication/QualitéEau"
path, dirs, files = next(os.walk(osp.join(dirname)))
for file in files:
    station_name = osp.splitext(file)[0].split('_')[-1]
    station_id = accessor._get_sampling_feature_uuid_from_name(station_name)
    print('Adding water quality report for station {}'.format(station_name))
    accessor.set_attachment(station_id, 2, osp.join(dirname, file))

accessor.close_connection()
