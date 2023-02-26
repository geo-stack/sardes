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
            ('pump_type_id', 'purge'),
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
})
