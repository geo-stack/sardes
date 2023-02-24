# -*- coding: utf-8 -*-
"""
Created on Tue Feb 21 13:31:00 2023

@author: User
"""
import pandas as pd

hg_values_xlsx_file = (
    "G:/Shared drives/2_PROJETS/231204_MELCCFP_Sardes_2023/3_LIVRABLES/"
    "valeur_parametre_BD_RSESQ_2019-07-24.xlsx")

hg_data = pd.read_excel(
    hg_values_xlsx_file,
    dtype={'No_Piézomètre': 'str'},
    )


# %%
CODE_PARAM_PHYS_CHIM = hg_data['CODE_PARAM_PHYS_CHIM'].unique()
for code_param in CODE_PARAM_PHYS_CHIM:
    subdata = hg_data[hg_data['CODE_PARAM_PHYS_CHIM'] == code_param]
    units = subdata['CODE_UNITE_MESURE'].unique()
    print(code_param, units)

# P -> mg / L

subdata = hg_data[hg_data['CODE_PARAM_PHYS_CHIM'] == 'ALCTOT10']
subdata = hg_data[hg_data['CODE_PARAM_PHYS_CHIM'] == 'AZOTOT10']
subdata = hg_data[hg_data['CODE_PARAM_PHYS_CHIM'] == 'CAINDI10']
subdata = hg_data[hg_data['CODE_PARAM_PHYS_CHIM'] == 'CAORDI10']

subdata = hg_data[hg_data['CODE_PARAM_PHYS_CHIM'] == 'TURBID10']
subdata = hg_data[hg_data['CODE_PARAM_PHYS_CHIM'] == 'AZOAMM10']
