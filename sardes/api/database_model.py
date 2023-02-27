# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

from collections import UserDict
from collections import namedtuple
import pandas as pd


class ReadOnlyDict(UserDict):
    def __init__(self, data: dict):
        super().__init__()
        self.data = data

    def __setitem__(self, key, val):
        raise NotImplementedError('This dictionary cannot be updated')

    def __delitem__(self, key):
        raise NotImplementedError('This dictionary does not allow delete')


Table = namedtuple(
    "Table",
    ('foreign_constraints', 'columns'),
    defaults=[(), ()]
    )

Column = namedtuple(
    "Column",
    ('name', 'dtype', 'desc', 'notnull', 'unique', 'unique_subset',
     'editable', 'default'),
    defaults=[False, False, (), True, None]
    )

DATABASE_CONCEPTUAL_MODEL = ReadOnlyDict({
    'manual_measurements': Table(
        columns=(
            Column(
                name='sampling_feature_uuid',
                dtype='object',
                desc=("A unique identifier that is used to reference the "
                      "observation well in the database in which the "
                      "manual measurement was made."),
                notnull=True,
                unique=True,
                unique_subset=('datetime',)
            ),
            Column(
                name='datetime',
                dtype='datetime64[ns]',
                desc=("A datetime object corresponding to the date and "
                      "time when the manual measurement was made in the "
                      "well."),
                notnull=True,
                unique=True,
                unique_subset=('sampling_feature_uuid',)
            ),
            Column(
                name='value',
                dtype='float64',
                desc=("The value of the water level that was measured "
                      "manually in the well."),
                notnull=True
            ),
            Column(
                name='notes',
                dtype='str',
                desc=("Any notes related to the manual measurement."),
            ),
        )
    ),
    'sonde_installations': Table(
        columns=(
            Column(
                name='sampling_feature_uuid',
                dtype='object',
                desc=("A unique identifier that is used to reference the "
                      "observation well in which the sonde are installed."),
                notnull=True
            ),
            Column(
                name='sonde_uuid',
                dtype='object',
                desc=("A unique identifier used to reference the sonde in "
                      "the database."),
                notnull=True
            ),
            Column(
                name='start_date',
                dtype='datetime64[ns]',
                desc=("The date and time at which the sonde was installed "
                      "in the well."),
                notnull=True,
            ),
            Column(
                name='end_date',
                dtype='datetime64[ns]',
                desc=("The date and time at which the sonde was removed "
                      "from the well.")
            ),
            Column(
                name='install_depth',
                dtype='float64',
                desc=("The depth at which the sonde was installed in "
                      "the well."),
                notnull=True,
            ),
            Column(
                name='install_note',
                dtype='str',
                desc=("A note related to the sonde installation."),
            ),
        )
    ),
    'repere_data': Table(
        columns=(
            Column(
                name='sampling_feature_uuid',
                dtype='object',
                desc=("A unique identifier that is used to reference the "
                      "observation well for which the repere data are "
                      "associated."),
                notnull=True,
            ),
            Column(
                name='top_casing_alt',
                dtype='float64',
                desc=("The altitude values given in meters of the top of "
                      "the observation wells' casing."),
                notnull=True,
            ),
            Column(
                name='casing_length',
                dtype='float64',
                desc=("The lenght of the casing above ground level "
                      "given in meters."),
                notnull=True,
            ),
            Column(
                name='start_date',
                dtype='datetime64[ns]',
                desc=("The date and time after which repere data "
                      "are valid."),
                notnull=True
            ),
            Column(
                name='end_date',
                dtype='datetime64[ns]',
                desc=("The date and time before which repere data "
                      "are valid.")
            ),
            Column(
                name='is_alt_geodesic',
                dtype='bool',
                desc=("Whether the top_casing_alt value is geodesic."),
                notnull=True
            ),
            Column(
                name='repere_note',
                dtype='str',
                desc=("Any note related to the repere data.")
            ),
        )
    ),
    'sondes_data': Table(
        foreign_constraints=(
            ('sonde_uuid', 'sonde_installations'),
        ),
        columns=(
            Column(
                name='sonde_serial_no',
                dtype='str',
                desc=("The serial number of the sonde."),
                unique=True,
                unique_subset=('sonde_model_id',),
            ),
            Column(
                name='sonde_model_id',
                dtype='object',
                desc=("The ID used to reference the sonde brand and model "
                      "in the database."),
                notnull=True,
                unique=True,
                unique_subset=('sonde_serial_no',),
            ),
            Column(
                name='date_reception',
                dtype='datetime64[ns]',
                desc=("The date when the sonde was added to the inventory.")
            ),
            Column(
                name='date_withdrawal',
                dtype='datetime64[ns]',
                desc=("The date when the sonde was removed from the "
                      "inventory.")
            ),
            Column(
                name='in_repair',
                dtype='bool',
                desc=("Indicate wheter the sonde is currently being "
                      "repaired."),
                notnull=True,
                default=False
            ),
            Column(
                name='out_of_order',
                dtype='bool',
                desc=("Indicate whether the sonde is out of order. "
                      "unconsolidated sediment."),
                notnull=True,
                default=False
            ),
            Column(
                name='lost',
                dtype='bool',
                desc=("Indicates whether the sonde has been lost."),
                notnull=True,
                default=False
            ),
            Column(
                name='off_network',
                dtype='bool',
                desc=("Indicate whether the sonde is currently being used "
                      "outside of the monitoring network."),
                notnull=True,
                default=False
            ),
            Column(
                name='sonde_notes',
                dtype='str',
                desc=("Any notes related to the sonde.")
            ),
        )
    ),
    'observation_wells_data': Table(
        foreign_constraints=(
            ('sampling_feature_uuid', 'manual_measurements'),
            ('sampling_feature_uuid', 'sonde_installations'),
            ('sampling_feature_uuid', 'repere_data'),
            ('sampling_feature_uuid', 'remarks'),
        ),
        columns=(
            Column(
                name='obs_well_id',
                dtype='str',
                desc=("The unique identifier of the observation well."),
                notnull=True,
                unique=True,
            ),
            Column(
                name='latitude',
                dtype='float64',
                desc=("The latitude of the observation well location "
                      "in decimal degrees.")
            ),
            Column(
                name='longitude',
                dtype='float64',
                desc=("The longitude of the observation well location "
                      "in decimal degrees.")
            ),
            Column(
                name='common_name',
                dtype='str',
                desc=("The human readable name of the well.")
            ),
            Column(
                name='municipality',
                dtype='str',
                desc=("The municipality where the well is installed.")
            ),
            Column(
                name='aquifer_type',
                dtype='str',
                desc=("Indicates if the well is open in the bedrock or "
                      "in the unconsolidated sediment.")
            ),
            Column(
                name='confinement',
                dtype='str',
                desc=("Indicates if the confinement at the well location "
                      "is confined, unconfined or semi-confined.")
            ),
            Column(
                name='aquifer_code',
                dtype='Int64',
                desc=("A code that represents the combination of aquifer "
                      "type and confinement for the well.")
            ),
            Column(
                name='in_recharge_zone',
                dtype='str',
                desc=("Indicates whether the observation well is located "
                      "in or in the proximity a recharge zone.")
            ),
            Column(
                name='is_influenced',
                dtype='str',
                desc=("Indicates whether the water levels measured in "
                      "that well are influenced or not by anthropic "
                      "phenomenon.")
            ),
            Column(
                name='elevation',
                dtype='float64',
                desc=("The elevation of the ground surface at the "
                      "observation well location in meters above "
                      "sea level.")
            ),
            Column(
                name='is_station_active',
                dtype='bool',
                desc=("Indicates whether the station is still "
                      "active or not."),
                notnull=True
            ),
            Column(
                name='obs_well_notes',
                dtype='str',
                desc=("Any notes related to the observation well.")
            ),
        ),
    ),
    'sonde_models_lib': Table(
        foreign_constraints=(
            ('sonde_model_id', 'sondes_data'),
        ),
        columns=(
            Column(
                name='sonde_brand_model',
                dtype='str',
                desc=("A sonde brand and model combination.")
            ),
            Column(
                name='sonde_brand',
                dtype='str',
                desc=("A sonde manufacturer."),
                notnull=True,
                unique=True,
                unique_subset=('sonde_model',)
            ),
            Column(
                name='sonde_model',
                dtype='str',
                desc=("A sonde model."),
                notnull=True,
                unique=True,
                unique_subset=('sonde_brand',)
            ),
        )
    ),
    # ---- Remarks
    'remarks': Table(
        columns=(
            Column(
                name='sampling_feature_uuid',
                dtype='object',
                desc=("The unique identifier of the observation well to which "
                      "the remark refers."),
                notnull=True,
            ),
            Column(
                name='remark_type_id',
                dtype='Int64',
                desc="The ID of the type of the remark."
            ),
            Column(
                name='period_start',
                dtype='datetime64[ns]',
                desc=("The start date of the period for which the remark "
                      "is valid.")
            ),
            Column(
                name='period_end',
                dtype='datetime64[ns]',
                desc=("The end date of the period for which the remark "
                      "is valid.")
            ),
            Column(
                name='remark_text',
                dtype='str',
                desc="The text of the remark."
            ),
            Column(
                name='remark_author',
                dtype='str',
                desc="The author of the remark."
            ),
            Column(
                name='remark_date',
                dtype='str',
                desc="The date the remark was made."
            ),
        ),
    ),
    'remark_types': Table(
        foreign_constraints=(
            ('remark_type_id', 'remarks'),
        ),
        columns=(
            Column(
                name='remark_type_code',
                dtype='str',
                desc=("The unique code of the remark type."),
                notnull=True,
                unique=True,
            ),
            Column(
                name='remark_type_name',
                dtype='str',
                desc=("The name of the remark type."),
                notnull=True,
                unique=True,
            ),
            Column(
                name='remark_type_desc',
                dtype='str',
                desc=("The description of the remark type.")
            ),
        )
    ),
    # ---- Hydrogeochemistry
    'pump_types': Table(
        foreign_constraints=(
            ('pump_type_id', 'purges'),
        ),
        columns=(
            Column(
                name='pump_type_name',
                dtype='str',
                desc=("A unique name to identify the pump type."),
                notnull=True,
                unique=True,
            ),
            Column(
                name='pump_type_desc',
                dtype='str',
                desc=("The description of the pump type."),
            ),
        )
    ),
    'hg_sampling_methods': Table(
        foreign_constraints=(
            ('hg_sampling_method_id', 'hg_surveys'),
        ),
        columns=(
            Column(
                name='hg_sampling_method_name',
                dtype='str',
                desc=("A unique name to identify the sampling method type."),
                notnull=True,
                unique=True,
            ),
            Column(
                name='hg_sampling_method_desc',
                dtype='str',
                desc=("The description of the sampling method type."),
            ),
        )
    ),
    'hg_params': Table(
        foreign_constraints=(
            ('hg_param_id', 'hg_field_measurements'),
            ('hg_param_id', 'hg_lab_results'),
        ),
        columns=(
            Column(
                name='hg_param_code',
                dtype='str',
                desc=("A unique code to identify the hydrogeochemical "
                      "parameter."),
                notnull=True,
                unique=True,
            ),
            Column(
                name='hg_param_name',
                dtype='str',
                desc=("The name of the hydrogeochemical parameter."
                      "Used when importing results from a lab report."),
            ),
            Column(
                name='hg_param_alt_name',
                dtype='str',
                desc=("Alternate names of the hydrogeochemical parameter."
                      "Each alternate names must be separated by a "
                      "semicolon. Used when importing data from a lab "
                      "report."),
            ),
            Column(
                name='cas_registry_number',
                dtype='str',
                desc=("The CAS Registry number of the parameter."),
            ),
            Column(
                name='measurement_units',
                dtype='str',
                desc=("The measurement units used to store the values of "
                      "the parameter."),
            ),
        )
    ),
    'hg_surveys': Table(
        foreign_constraints=(
            ('hg_survey_id', 'hg_field_measurements'),
            ('hg_survey_id', 'purges'),
            ('lab_sample_id', 'hg_lab_results'),
        ),
        columns=(
            Column(
                name='sampling_feature_uuid',
                dtype='object',
                desc=("The unique identifier of the observation well in which "
                      "the survey was made."),
                notnull=True,
            ),
            Column(
                name='hg_survey_datetime',
                dtype='datetime',
                desc=("The date and time when the survey was made."),
                notnull=True,
            ),
            Column(
                name='hg_survey_depth',
                dtype='float64',
                desc=("The depth in the well at which the survey was made."),
            ),
            Column(
                name='hg_survey_operator',
                dtype='str',
                desc=("The name of the person that made the survey."),
            ),
            Column(
                name='hg_sampling_method_id',
                dtype='Int64',
                desc=("The ID of the method type used to do the survey."),
            ),
            Column(
                name='lab_sample_id',
                dtype='str',
                desc=("The ID given to the sample by the lab."),
            ),
            Column(
                name='lab_report_date',
                dtype='datetime',
                desc=("The date of the sample lab report."),
            ),
            Column(
                name='sample_filtered',
                dtype='bool',
                desc=("Whether the sample was filtered or not."),
            ),
            Column(
                name='survey_note',
                dtype='str',
                desc=("Notes related to the survey."),
            ),
        )
    ),
    'hg_field_measurements': Table(
        columns=(
            Column(
                name='hg_survey_id',
                dtype='Int64',
                desc=("The ID of the survey during which "
                      "the field measurement was made."),
                notnull=True,
            ),
            Column(
                name='hg_param_id',
                dtype='Int64',
                desc=("The ID of the parameter corresponding to the "
                      "field measurement."),
                notnull=True,
            ),
            Column(
                name='hg_param_value',
                dtype='str',
                desc=("The value of the field measurement."),
                notnull=True,
            ),
            Column(
                name='lim_detection',
                dtype='float64',
                desc=("The limit of detection of the method used to "
                      "take the field measurement."),
            ),
            Column(
                name='lim_quantification',
                dtype='float64',
                desc=("The limit of quantification of the method used to "
                      "take the field measurement."),
            ),
        )
    ),
    'hg_lab_results': Table(
        columns=(
            Column(
                name='lab_sample_id',
                dtype='Int64',
                desc=("The ID given to the sample by the lab."),
                notnull=True,
            ),
            Column(
                name='hg_param_id',
                dtype='Int64',
                desc=("The ID of the parameter corresponding to the "
                      "lab result."),
                notnull=True,
            ),
            Column(
                name='hg_param_value',
                dtype='str',
                desc=("The value of the lab result."),
                notnull=True,
            ),
            Column(
                name='lim_detection',
                dtype='float64',
                desc=("The limit of detection of the method used to "
                      "analyse the result."),
            ),
            Column(
                name='lim_quantification',
                dtype='float64',
                desc=("The limit of quantification of the method used to "
                      "analyse the result."),
            ),
            Column(
                name='code_analysis_method',
                dtype='str',
                desc=("The code of the method used to analyse the result."),
            ),
        )
    ),
    'purges': Table(
        columns=(
            Column(
                name='hg_survey_id',
                dtype='Int64',
                desc=("The ID of the survey when the purge was made."),
                notnull=True,
            ),
            Column(
                name='purge_sequence_no',
                dtype='Int64',
                desc=("The number of the purge sequence."),
                notnull=True,
            ),
            Column(
                name='purge_seq_start',
                dtype='datetime',
                desc=("The start date and time of the purge sequence."),
                notnull=True,
            ),
            Column(
                name='purge_seq_end',
                dtype='datetime',
                desc=("The end date and time of the purge sequence."),
                notnull=True,
            ),
            Column(
                name='purge_outflow',
                dtype='float64',
                desc=("The purge outflow in L/min."),
                notnull=True,
            ),
            Column(
                name='pump_type_id',
                dtype='Int64',
                desc=("The ID of the pump type used to do the purge."),
                notnull=True,
            ),
            Column(
                name='pumping_depth',
                dtype='float64',
                desc=("The pumping depth."),
                notnull=True,
            ),
            Column(
                name='static_water_level',
                dtype='float64',
                desc=("The sttic water level."),
                notnull=True,
            ),
        )
    ),
})
