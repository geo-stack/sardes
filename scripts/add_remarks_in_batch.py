# -*- coding: utf-8 -*-
"""
A Script to add remarks data in batch from a csv file.
"""
import pandas as pd
from sardes.database.accessors.accessor_sardes_lite import (
    DatabaseAccessorSardesLite)

remarks_xlsx_file = (
    "G:/Shared drives/2_PROJETS/231204_MELCCFP_Sardes_2023/3_LIVRABLES/"
    "commentaires_BD_RSESQ_2019-07-24.xlsx")

remarks_data = pd.read_excel(
    remarks_xlsx_file,
    dtype={'sampling_feature_uuid': 'str'},
    parse_dates=['remark_date', 'period_start', 'period_end']
    )

# %%

database = "D:/Desktop/rsesq_prod_02-04-2021.db"
dbaccessor = DatabaseAccessorSardesLite(database)
dbaccessor.connect()

# Populate the 'remark_types' table.
remark_types_values = [
    {'remark_type_code': 'C',
     'remark_type_name': 'Correction',
     'remark_type_desc': ("Une correction appliquée aux données de suivi "
                          "sur une période donnée")
     },
    {'remark_type_code': 'I',
     'remark_type_name': 'Incertitude',
     'remark_type_desc': ("Une incertitude sur les données de suivi "
                          "pour une période donnée")
     },
    {'remark_type_code': 'N',
     'remark_type_name': 'Note',
     'remark_type_desc': ("Note interne sur les données de suivi")
     }
    ]
dbaccessor.add(name='remark_types', values=remark_types_values)


# Add remarks to the database.
for index, row in remarks_data.iterrows():
    row = row.dropna()
    _dict = row.to_dict()
    _dict['sampling_feature_uuid'] = (
        dbaccessor._get_sampling_feature_uuid_from_name(
            _dict['sampling_feature_uuid'])
        )
    dbaccessor.add(name='remarks', values=[_dict])

dbaccessor.close_connection()
