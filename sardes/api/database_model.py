# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

from collections import UserDict


class ReadOnlyDict(UserDict):
    def __init__(self, data: dict):
        super().__init__()
        self.data = data

    def __setitem__(self, key, val):
        raise NotImplementedError('This dictionary cannot be updated')

    def __delitem__(self, key):
        raise NotImplementedError('This dictionary does not allow delete')


DATABASE_CONCEPTUAL_MODEL = ReadOnlyDict({
    'manual_measurements': ReadOnlyDict({
        'foreign_constraints': (),
        'unique_constraints': (
            ('datetime', 'sampling_feature_uuid')
        ),
        'notnull_constraints': (
            'sampling_feature_uuid',
            'datetime',
            'value'
        ),
        'columns': ReadOnlyDict({
            'sampling_feature_uuid': ReadOnlyDict({
                'dtype': 'object',
                'desc': ("A unique identifier that is used to reference the "
                         "observation well in the database in which the "
                         "manual measurement was made."),
            }),
            'datetime': ReadOnlyDict({
                'dtype': 'datetime64[ns]',
                'desc': ("A datetime object corresponding to the date and "
                         "time when the manual measurement was made in the "
                         "well.")
            }),
            'value': ReadOnlyDict({
                'dtype': 'float64',
                'desc': ("The value of the water level that was measured "
                         "manually in the well.")
            }),
            'notes': ReadOnlyDict({
                'dtype': 'str',
                'desc': ("Any notes related to the manual measurement.")
            })
        })
    }),
    'sonde_installations': ReadOnlyDict({
        'foreign_constraints': (),
        'unique_constraints': (),
        'notnull_constraints': (),
        'columns': ReadOnlyDict({
            'sampling_feature_uuid': ReadOnlyDict({
                'dtype': 'object',
                'desc': ("A unique identifier that is used to reference the "
                         "observation well in which the sonde are installed.")
            }),
            'sonde_uuid': ReadOnlyDict({
                'dtype': 'object',
                'desc': ("A unique identifier used to reference each sonde in "
                         "the database.")
            }),
            'start_date': ReadOnlyDict({
                'dtype': 'datetime64[ns]',
                'desc': ("The date and time at which the sonde was installed "
                         "in the well.")
            }),
            'end_date': ReadOnlyDict({
                'dtype': 'datetime64[ns]',
                'desc': ("The date and time at which the sonde was removed "
                         "from the well.")
            }),
            'install_depth': ReadOnlyDict({
                'dtype': 'float',
                'desc': ("The depth at which the sonde was installed in "
                         "the well.")
            })
        })
    }),
    'repere_data': ReadOnlyDict({
        'foreign_constraints': (),
        'unique_constraints': (),
        'notnull_constraints': (),
        'columns': ReadOnlyDict({
            'sampling_feature_uuid': ReadOnlyDict({
                'dtype': 'object',
                'desc': ("A unique identifier that is used to reference the "
                         "observation well for which the repere data are "
                         "associated.")
            }),
            'top_casing_alt': ReadOnlyDict({
                'dtype': 'float',
                'desc': ("The altitude values given in meters of the top of "
                         "the observation wells' casing.")
            }),
            'casing_length': ReadOnlyDict({
                'dtype': 'float',
                'desc': ("The lenght of the casing above ground level "
                         "given in meters.")
            }),
            'start_date': ReadOnlyDict({
                'dtype': 'datetime64[ns]',
                'desc': ("The date and time after which repere data "
                         "are valid.")
            }),
            'end_date': ReadOnlyDict({
                'dtype': 'datetime64[ns]',
                'desc': ("The date and time before which repere data "
                         "are valid.")
            }),
            'is_alt_geodesic': ReadOnlyDict({
                'dtype': 'bool',
                'desc': ("Whether the top_casing_alt value is geodesic.")
            }),
            'repere_note': ReadOnlyDict({
                'dtype': 'str',
                'desc': ("Any note related to the repere data.")
            }),
        })
    }),
    'sondes_data': ReadOnlyDict({
        'foreign_constraints': (
            ('sonde_uuid', 'sonde_installations'),
        ),
        'unique_constraints': (),
        'notnull_constraints': (),
        'columns': ReadOnlyDict({
            'sonde_serial_no': ReadOnlyDict({
                'dtype': 'str',
                'desc': ("The serial number of the sonde.")
            }),
            'sonde_model_id': ReadOnlyDict({
                'dtype': 'object',
                'desc': ("The ID used to reference the sonde brand and model "
                         "in the database.")
            }),
            'date_reception': ReadOnlyDict({
                'dtype': 'datetime64[ns]',
                'desc': ("The date when the sonde was added to the inventory.")
            }),
            'date_withdrawal': ReadOnlyDict({
                'dtype': 'datetime64[ns]',
                'desc': ("The date when the sonde was removed from the "
                         "inventory.")
            }),
            'in_repair': ReadOnlyDict({
                'dtype': 'bool',
                'desc': ("Indicate wheter the sonde is currently being "
                         "repaired.")
            }),
            'out_of_order': ReadOnlyDict({
                'dtype': 'bool',
                'desc': ("Indicate whether the sonde is out of order. "
                         "unconsolidated sediment.")
            }),
            'lost': ReadOnlyDict({
                'dtype': 'bool',
                'desc': ("Indicates whether the sonde has been lost.")
            }),
            'off_network': ReadOnlyDict({
                'dtype': 'bool',
                'desc': ("Indicate whether the sonde is currently being used "
                         "outside of the monitoring network.")
            }),
            'sonde_notes': ReadOnlyDict({
                'dtype': 'str',
                'desc': ("Any notes related to the sonde.")
            }),
        })
    }),
    'observation_wells_data': ReadOnlyDict({
        'foreign_constraints': (
            ('sampling_feature_uuid', 'manual_measurements'),
            ('sampling_feature_uuid', 'sonde_installations'),
            ('sampling_feature_uuid', 'repere_data'),
        ),
        'unique_constraints': (
            ['obs_well_id']
        ),
        'notnull_constraints': (
            'obs_well_id',
            'is_station_active'
        ),
        'columns': ReadOnlyDict({
            'obs_well_id': ReadOnlyDict({
                'dtype': 'str',
                'desc': ("The unique identifier of the observation well.")
            }),
            'latitude': ReadOnlyDict({
                'dtype': 'float',
                'desc': ("The latitude of the observation well location "
                         "in decimal degrees.")
            }),
            'longitude': ReadOnlyDict({
                'dtype': 'float',
                'desc': ("The longitude of the observation well location "
                         "in decimal degrees.")
            }),
            'common_name': ReadOnlyDict({
                'dtype': 'str',
                'desc': ("The human readable name of the well.")
            }),
            'municipality': ReadOnlyDict({
                'dtype': 'str',
                'desc': ("The municipality where the well is installed.")
            }),
            'aquifer_type': ReadOnlyDict({
                'dtype': 'str',
                'desc': ("Indicates if the well is open in the bedrock or "
                         "in the unconsolidated sediment.")
            }),
            'confinement': ReadOnlyDict({
                'dtype': 'str',
                'desc': ("Indicates if the confinement at the well location "
                         "is confined, unconfined or semi-confined.")
            }),
            'aquifer_code': ReadOnlyDict({
                'dtype': 'Int64',
                'desc': ("A code that represents the combination of aquifer "
                         "type and confinement for the well.")
            }),
            'in_recharge_zone': ReadOnlyDict({
                'dtype': 'str',
                'desc': ("Indicates whether the observation well is located "
                         "in or in the proximity a recharge zone.")
            }),
            'is_influenced': ReadOnlyDict({
                'dtype': 'str',
                'desc': ("Indicates whether the water levels measured in "
                         "that well are influenced or not by anthropic "
                         "phenomenon.")
            }),
            'elevation': ReadOnlyDict({
                'dtype': 'float',
                'desc': ("The elevation of the ground surface at the "
                         "observation well location in meters above "
                         "sea level.")
            }),
            'is_station_active': ReadOnlyDict({
                'dtype': 'bool',
                'desc': ("Indicates whether the station is still "
                         "active or not.")
            }),
            'obs_well_notes': ReadOnlyDict({
                'dtype': 'str',
                'desc': ("Any notes related to the observation well.")
            }),
        })
    }),
    'sonde_models_lib': ReadOnlyDict({
        'foreign_constraints': (
            ('sonde_model_id', 'sondes_data'),
        ),
        'unique_constraints': (),
        'notnull_constraints': (),
        'columns': ReadOnlyDict({
            'sonde_brand_model': ReadOnlyDict({
                'dtype': 'str',
                'desc': ("A sonde brand and model combination.")
            }),
            'sonde_brand': ReadOnlyDict({
                'dtype': 'str',
                'desc': ("A sonde manufacturer.")
            }),
            'sonde_model': ReadOnlyDict({
                'dtype': 'str',
                'desc': ("A sonde model.")
            }),
        })
    }),
})
