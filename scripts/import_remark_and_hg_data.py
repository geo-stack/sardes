# -*- coding: utf-8 -*-
"""
Created on Tue Feb 21 13:31:00 2023
@author: User
"""
import numpy as np
import pandas as pd
from sardes.database.accessors.accessor_sardes_lite import (
    DatabaseAccessorSardesLite)
import shutil

# %% Update the database.
database = "D:/Desktop/rsesq_prod_28-12-2022_jsg.db"
shutil.copy("D:/Desktop/rsesq_prod_28-12-2022.db", database)

dbaccessor = DatabaseAccessorSardesLite(database)
dbaccessor.update_database()

# %%
print("Adding remarks data...")

remarks_xlsx_file = (
    "G:/Shared drives/2_PROJETS/231204_MELCCFP_Sardes_2023/3_LIVRABLES/"
    "Annexe A/BD_RSESQ_2019-07-24 commentaires.xlsx")

remarks_data = pd.read_excel(
    remarks_xlsx_file,
    dtype={'sampling_feature_uuid': 'str'},
    parse_dates=['remark_date', 'period_start', 'period_end']
    )

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

# %%
print("Adding pump types...")

type_pompe_xlsx_file = (
    "G:/Shared drives/2_PROJETS/231204_MELCCFP_Sardes_2023/3_LIVRABLES/"
    "Annexe A/BD_RSESQ_2019-07-24 type_pompe.xlsx"
    )
type_pompe_xlsx = pd.read_excel(
    type_pompe_xlsx_file,
    usecols=['Desc_type_pomp']
    )

pump_types = type_pompe_xlsx[['Desc_type_pomp']].copy()
pump_types.columns = ['pump_type_name']

dbaccessor.add(name='pump_types', values=pump_types.to_dict('index').values())
pump_types = dbaccessor.get(name='pump_types')

# %%
print("Adding sampling methods...")

sampling_methods_xlsx_file = (
    "G:/Shared drives/2_PROJETS/231204_MELCCFP_Sardes_2023/3_LIVRABLES/"
    "Annexe A/BD_RSESQ_2019-07-24 mode_echantillonnage.xlsx"
    )
sampling_methods = pd.read_excel(
    sampling_methods_xlsx_file,
    usecols=['DESC_MODE_ECHANT']
    )
sampling_methods.columns = ['hg_sampling_method_name']


dbaccessor.add(
    name='hg_sampling_methods',
    values=sampling_methods.to_dict('index').values())
hg_sampling_methods = dbaccessor.get(name='hg_sampling_methods')

# %%
print("Adding measurement units...")

hg_values_xlsx_file = (
    "G:/Shared drives/2_PROJETS/231204_MELCCFP_Sardes_2023/3_LIVRABLES/"
    "Annexe A/BD_RSESQ_2019-07-24 valeur_parametre.xlsx")
hg_values = pd.read_excel(
    hg_values_xlsx_file,
    dtype={'No_Piézomètre': 'str'},
    )

hg_units_xlsx_file = (
    "G:/Shared drives/2_PROJETS/231204_MELCCFP_Sardes_2023/3_LIVRABLES/"
    "Annexe A/BD_RSESQ_2019-07-24 unite_mesure.xlsx"
    )
hg_units_xlsx = pd.read_excel(hg_units_xlsx_file)

unique_units = []
for index, row in hg_values.iterrows():
    code = row['CODE_UNITE_MESURE']
    nom = hg_units_xlsx[
        hg_units_xlsx['CODE_UNITE_MESURE'] == code
        ]['NOM_UNITE_MESURE'].values[0]
    unique_units.append(nom)
unique_units = np.unique(unique_units)

measurement_units = pd.DataFrame(
    data=[],
    index=unique_units,
    columns=['meas_units_name', 'meas_units_desc']
    )
measurement_units.index.name = 'meas_units_abb'

measurement_units.loc['AU', 'meas_units_name'] = (
    "unité de turbidité absorbante")
measurement_units.loc['AU', 'meas_units_desc'] = (
    "Permet d'exprimer la lumière absorbée par une substance "
    "lorsqu'elle est exposée à une source lumineuse.")
measurement_units.loc['BQ/L', 'meas_units_name'] = (
    "becquerel par litre")
measurement_units.loc['BQ/L', 'meas_units_desc'] = (
    "Permet d'exprimer l'activité radioactive d'une substance "
    "dissoute dans un liquide.")
measurement_units.loc['UTN', 'meas_units_name'] = (
    "unité de turbidité néphélométrique")
measurement_units.loc['UTN', 'meas_units_desc'] = (
    "Permet d'exprimer la quantité de lumière dispersée par les "
    "particules en suspension dans le liquide.")
measurement_units.loc['mg/L', 'meas_units_name'] = (
    "milligramme par litre")
measurement_units.loc['mg/L', 'meas_units_desc'] = (
    "Permet d'exprimer la concentration d'une substance dans un liquide.")
measurement_units.loc['mg/L C', 'meas_units_name'] = (
    "milligramme de carbone par litre")
measurement_units.loc['mg/L C', 'meas_units_desc'] = (
    "Permet d'exprimer la concentration de carbone organique dissous "
    "dans un liquide.")
measurement_units.loc['mg/L CaCO3', 'meas_units_name'] = (
    "milligramme par litre de carbonate de calcium équivalent")
measurement_units.loc['mg/L CaCO3', 'meas_units_desc'] = (
    "Permet d'exprimer la dureté de l'eau.")
measurement_units.loc['mg/L N', 'meas_units_name'] = (
    "milligramme d'azote par litre")
measurement_units.loc['mg/L N', 'meas_units_desc'] = (
    "Permet d'exprimer la concentration d'azote dans un liquide.")
measurement_units.loc['mg/L S-2', 'meas_units_name'] = (
    "milligramme par litre de sulfure")
measurement_units.loc['mg/L S-2', 'meas_units_desc'] = (
    "Permet d'exprimer la concentration de sulfure dans un liquide.")
measurement_units.loc['µg/L', 'meas_units_name'] = (
    "microgramme par litre")
measurement_units.loc['µg/L', 'meas_units_desc'] = (
    "Permet d'exprimer de petites quantités de substances dans un liquide.")
measurement_units.loc['µmhos/cm', 'meas_units_name'] = (
    "microsiemens par centimètre")
measurement_units.loc['µmhos/cm', 'meas_units_desc'] = (
    "Permet d'exprimer la conductivité électrique de l'eau ou d'une solution.")
measurement_units.loc['‰', 'meas_units_name'] = (
    "parties par millier")
measurement_units.loc['‰', 'meas_units_desc'] = (
    "Permet d'exprimer les concentrations de substances dans l'eau ou l'air.")

measurement_units = measurement_units.reset_index()

dbaccessor.add(
    name='measurement_units',
    values=measurement_units.to_dict('index').values())
measurement_units = dbaccessor.get(name='measurement_units')


# %% Add HG Params.
print("Adding HG params...")

hg_params_xlsx_file = (
    "G:/Shared drives/2_PROJETS/231204_MELCCFP_Sardes_2023/3_LIVRABLES/"
    "Annexe A/BD_RSESQ_2019-07-24 params_physico_chimique.xlsx"
    )
hg_params = pd.read_excel(
    hg_params_xlsx_file,
    )
hg_params.columns = [
    'hg_param_code', 'hg_param_name', 'cas_registry_number']

# Remove all codes for which no values are saved in the database.
hg_values_xlsx_file = (
    "G:/Shared drives/2_PROJETS/231204_MELCCFP_Sardes_2023/3_LIVRABLES/"
    "Annexe A/BD_RSESQ_2019-07-24 valeur_parametre.xlsx")
hg_values = pd.read_excel(
    hg_values_xlsx_file,
    dtype={'No_Piézomètre': 'str'},
    )
used_param_codes = hg_values['CODE_PARAM_PHYS_CHIM'].unique()

mask = hg_params['hg_param_code'].isin(used_param_codes)
hg_params = hg_params[mask]

dbaccessor.add(name='hg_params', values=hg_params.to_dict('index').values())
hg_params = dbaccessor.get(name='hg_params')


# %% Add HG Surveys
print("Adding HG surveys...")

physico_chimie_xlsx_file = (
    "G:/Shared drives/2_PROJETS/231204_MELCCFP_Sardes_2023/3_LIVRABLES/"
    "Annexe A/BD_RSESQ_2019-07-24 physico_chimie.xlsx"
    )
physico_chimie_xlsx = pd.read_excel(physico_chimie_xlsx_file)

hg_surveys = pd.DataFrame(
    index=physico_chimie_xlsx.index,
    columns=['sampling_feature_uuid',
             'hg_survey_datetime',
             'hg_survey_depth',
             'hg_survey_operator',
             'hg_sampling_method_id',
             'sample_filtered',
             'survey_note'
             ]
    )
hg_surveys['hg_survey_datetime'] = physico_chimie_xlsx['DATE_HRE_RELV']
hg_surveys['hg_survey_depth'] = physico_chimie_xlsx['PROFOND_RELV_HG']
hg_surveys['hg_survey_operator'] = physico_chimie_xlsx['PRELEVE_PAR']
hg_surveys['sample_filtered'] = (
    physico_chimie_xlsx['Échant_Filtré'].astype('Int64'))
hg_surveys['survey_note'] = physico_chimie_xlsx['Note_terrain']

obs_wells = dbaccessor.get(name='observation_wells_data')
for index, row in hg_surveys.iterrows():
    sta_name = physico_chimie_xlsx.loc[index, 'No_Piézomètre']

    hg_surveys.loc[index, 'sampling_feature_uuid'] = (
        obs_wells[obs_wells.obs_well_id == sta_name].index[0])

    hg_surveys.loc[index, 'hg_sampling_method_id'] = (
        physico_chimie_xlsx.loc[index, 'MODE_ECHANT'])

dbaccessor.add(name='hg_surveys', values=hg_surveys.to_dict('index').values())
hg_surveys = dbaccessor.get(name='hg_surveys')


# %%
print("Adding HG param values...")

val_param_xlsx_file = (
    "G:/Shared drives/2_PROJETS/231204_MELCCFP_Sardes_2023/3_LIVRABLES/"
    "Annexe A/BD_RSESQ_2019-07-24 valeur_parametre.xlsx"
    )
val_param_xlsx = pd.read_excel(val_param_xlsx_file)

lim_detect_xlsx_file = (
    "G:/Shared drives/2_PROJETS/231204_MELCCFP_Sardes_2023/3_LIVRABLES/"
    "Annexe A/BD_RSESQ_2019-07-24 lim_detection.xlsx"
    )
lim_detect_xlsx = pd.read_excel(lim_detect_xlsx_file)

hg_param_values = pd.DataFrame(
    index=val_param_xlsx.index,
    columns=['hg_survey_id',
             'hg_param_id',
             'hg_param_value',
             'lim_detection',
             'meas_units_id',
             'lab_sample_id',
             'lab_name',
             'lab_report_date',
             'method',
             'notes']
    )

hg_param_values['hg_param_value'] = val_param_xlsx['MESR_PARAM']
hg_param_values['lab_sample_id'] = val_param_xlsx['No_Échan_Labo']
hg_param_values['method'] = val_param_xlsx['No_Meth_Analyse']

meas_units = dbaccessor.get(name='measurement_units')
hg_params = dbaccessor.get(name='hg_params')
hg_surveys = dbaccessor.get(name='hg_surveys')
for index, row in val_param_xlsx.iterrows():

    # Set 'hg_survey_id'.
    sta_name = row['No_Piézomètre']
    sta_uuid = obs_wells[obs_wells.obs_well_id == sta_name].index[0]
    hg_survey_datetime = row['DATE_HRE_RELV_HG']
    hg_survey_id = hg_surveys[
        (hg_surveys.sampling_feature_uuid == sta_uuid) &
        (hg_surveys.hg_survey_datetime == hg_survey_datetime)
        ].index[0]
    hg_param_values.loc[index, 'hg_survey_id'] = hg_survey_id

    # Set 'hg_param_id'.
    CODE_PARAM_PHYS_CHIM = row['CODE_PARAM_PHYS_CHIM']
    hg_param_id = hg_params[
        hg_params.hg_param_code == CODE_PARAM_PHYS_CHIM
        ].index[0]
    hg_param_values.loc[index, 'hg_param_id'] = hg_param_id

    # Set 'lab_name'.
    lab_name = physico_chimie_xlsx[
        (physico_chimie_xlsx.No_Piézomètre == sta_name) &
        (physico_chimie_xlsx.DATE_HRE_RELV == hg_survey_datetime)
        ]['NO_LABO_TRAITANT'].values[0]
    if not pd.isnull(lab_name):
        hg_param_values.loc[index, 'lab_name'] = str(int(lab_name))

    # Set 'lab_report_date'.
    lab_report_date = physico_chimie_xlsx[
        (physico_chimie_xlsx.No_Piézomètre == sta_name) &
        (physico_chimie_xlsx.DATE_HRE_RELV == hg_survey_datetime)
        ]['DATE_RAPPORT_ANALYSE'].values[0]
    hg_param_values.loc[index, 'lab_report_date'] = lab_report_date

    # Set 'meas_units_id'.
    val_units = hg_units_xlsx[
        hg_units_xlsx.CODE_UNITE_MESURE == row['CODE_UNITE_MESURE']
        ]['NOM_UNITE_MESURE'].values[0]
    meas_units_id = meas_units[
        meas_units.meas_units_abb == val_units
        ].index[0]
    hg_param_values.loc[index, 'meas_units_id'] = meas_units_id

    lim_detect_param = lim_detect_xlsx[
        lim_detect_xlsx.CODE_PARAM_PHYS_CHIM == CODE_PARAM_PHYS_CHIM
        ]
    lim_detect_param = lim_detect_param[
        lim_detect_param.DATE_LIM_DETECTION <= row['DATE_LIM_DETECTION']
        ]
    try:
        lim_detect = lim_detect_param.iloc[-1]['LIM_DETECTION']
    except IndexError:
        pass
    else:
        hg_param_values.loc[index, 'lim_detection'] = lim_detect


hg_param_values['lab_report_date'] = pd.to_datetime(
    hg_param_values['lab_report_date'])

dbaccessor.add(
    name='hg_param_values',
    values=hg_param_values.to_dict('index').values()
    )
hg_param_values = dbaccessor.get(name='hg_param_values')

# %%
print("Add purge data...")

purge_xlsx_file = (
    "G:/Shared drives/2_PROJETS/231204_MELCCFP_Sardes_2023/3_LIVRABLES/"
    "Annexe A/BD_RSESQ_2019-07-24 purge.xlsx"
    )
purge_xlsx = pd.read_excel(purge_xlsx_file)

purges = pd.DataFrame(
    index=purge_xlsx.index,
    columns=["hg_survey_id",
             "purge_sequence_no",
             "purge_seq_start",
             "purge_seq_end",
             "purge_outflow",
             "pump_type_id",
             "pumping_depth",
             "static_water_level"]
    )

purges["purge_sequence_no"] = purge_xlsx['Séquence']
purges["purge_seq_start"] = purge_xlsx['Date_Heure_Debut_Pomp']
purges["purge_seq_end"] = purge_xlsx['Date_Heure_Fin_Pomp']
purges["pumping_depth"] = purge_xlsx['Profondeur_Pompage']
purges["purge_outflow"] = purge_xlsx['Debit_Pompé']


pump_types = dbaccessor.get(name='pump_types')
hg_surveys = dbaccessor.get(name='hg_surveys')
obs_wells = dbaccessor.get(name='observation_wells_data')
for index, row in purge_xlsx.iterrows():
    # Set pump type ID.
    pump_type_name = row['type_pomp']
    pump_type_id = pump_types[
        pump_types.pump_type_name == pump_type_name
        ].index[0]
    purges.loc[index, "pump_type_id"] = pump_type_id

    # Set HG survey ID.
    sta_name = row['No_Piézomètre']
    sta_uuid = obs_wells[obs_wells.obs_well_id == sta_name].index[0]
    hg_survey_datetime = row['DATE_HRE_RELV_HG']
    hg_survey_id = hg_surveys[
        (hg_surveys.sampling_feature_uuid == sta_uuid) &
        (hg_surveys.hg_survey_datetime == hg_survey_datetime)
        ].index[0]
    purges.loc[index, 'hg_survey_id'] = hg_survey_id

dbaccessor.add(name='purges', values=purges.to_dict('index').values())
purges = dbaccessor.get(name='purges')
