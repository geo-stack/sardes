# -*- coding: utf-8 -*-
"""
A Script to add remarks data in batch from a csv file.
"""
import pandas as pd
from sardes.database.accessors.accessor_sardes_lite import (
    DatabaseAccessorSardesLite)

remarks_csv_file = (
    "G:/Shared drives/2_PROJETS/231204_MELCCFP_Sardes_2023/"
    "3_LIVRABLES/commentaires_BD_RSESQ_2019-07-24_formatted.csv")

remarks_data = pd.read_csv(
    remarks_csv_file,
    dtype={'sampling_feature_uuid': 'str'},
    parse_dates=['remark_date']
    )

database = "D:/Desktop/rsesq_prod_02-04-2021.db"
dbaccessor = DatabaseAccessorSardesLite(database)
dbaccessor.connect()

for index, row in remarks_data.iterrows():
    row = row.dropna()
    _dict = row.to_dict()
    _dict['sampling_feature_uuid'] = (
        dbaccessor._get_sampling_feature_uuid_from_name(
            _dict['sampling_feature_uuid'])
        )
    dbaccessor.add(name='remarks', values=[_dict])

dbaccessor.close_connection()
