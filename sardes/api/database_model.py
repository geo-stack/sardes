# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

DATABASE_CONCEPTUAL_MODEL = {
    'manual_measurements': {
        'foreign_constraints': [],
        'columns': {
            'sampling_feature_uuid': {
                'dtype': 'object',
                'desc': ("A unique identifier that is used to reference the "
                         "observation well in the database in which the "
                         "manual measurement was made."),
            },
            'datetime': {
                'dtype': 'datetime64[ns]',
                'desc': ("A datetime object corresponding to the date and "
                         "time when the manual measurement was made in the "
                         "well.")
            },
            'value': {
                'dtype': 'float64',
                'desc': ("The value of the water level that was measured "
                         "manually in the well.")
            },
            'notes': {
                'dtype': 'str',
                'desc': ("Any notes related to the manual measurement.")
            }
        }
    },
    'sonde_installations': {
        'foreign_constraints': [],
        'columns': {
            'sampling_feature_uuid': {
                'dtype': 'object',
                'desc': ("A unique identifier that is used to reference the "
                         "observation well in which the sonde are installed.")
            },
            'sonde_uuid': {
                'dtype': 'object',
                'desc': ("A unique identifier used to reference each sonde in "
                         "the database.")
            },
            'start_date': {
                'dtype': 'datetime64[ns]',
                'desc': ("The date and time at which the sonde was installed "
                         "in the well.")
            },
            'end_date': {
                'dtype': 'datetime64[ns]',
                'desc': ("The date and time at which the sonde was removed "
                         "from the well.")
            },
            'install_depth': {
                'dtype': 'float',
                'desc': ("The depth at which the sonde was installed in "
                         "the well.")
            }
        }
    },
    'repere_data': {
        'foreign_constraints': [],
        'columns': {
            'sampling_feature_uuid': {
                'dtype': 'object',
                'desc': ("A unique identifier that is used to reference the "
                         "observation well for which the repere data are "
                         "associated.")
            },
            'top_casing_alt': {
                'dtype': 'float',
                'desc': ("The altitude values given in meters of the top of "
                         "the observation wells' casing.")
            },
            'casing_length': {
                'dtype': 'float',
                'desc': ("The lenght of the casing above ground level "
                         "given in meters.")
            },
            'start_date': {
                'dtype': 'datetime64[ns]',
                'desc': ("The date and time after which repere data "
                         "are valid.")
            },
            'end_date': {
                'dtype': 'datetime64[ns]',
                'desc': ("The date and time before which repere data "
                         "are valid.")
            },
            'is_alt_geodesic': {
                'dtype': 'bool',
                'desc': ("Whether the top_casing_alt value is geodesic.")
            },
            'repere_note': {
                'dtype': 'str',
                'desc': ("Any note related to the repere data.")
            },
        }
    },
    'sondes_data': {
        'foreign_constraints': [
            ('sonde_uuid', 'sonde_installations')],
        'columns': {
            'sonde_serial_no': {
                'dtype': 'str',
                'desc': ("The serial number of the sonde.")
            },
            'sonde_model_id': {
                'dtype': 'object',
                'desc': ("The ID used to reference the sonde brand and model "
                         "in the database.")
            },
            'date_reception': {
                'dtype': 'datetime64[ns]',
                'desc': ("The date when the sonde was added to the inventory.")
            },
            'date_withdrawal': {
                'dtype': 'datetime64[ns]',
                'desc': ("The date when the sonde was removed from the "
                         "inventory.")
            },
            'in_repair': {
                'dtype': 'bool',
                'desc': ("Indicate wheter the sonde is currently being "
                         "repaired.")
            },
            'out_of_order': {
                'dtype': 'bool',
                'desc': ("Indicate whether the sonde is out of order. "
                         "unconsolidated sediment.")
            },
            'lost': {
                'dtype': 'bool',
                'desc': ("Indicates whether the sonde has been lost.")
            },
            'off_network': {
                'dtype': 'bool',
                'desc': ("Indicate whether the sonde is currently being used "
                         "outside of the monitoring network.")
            },
            'sonde_notes': {
                'dtype': 'str',
                'desc': ("Any notes related to the sonde.")
            },
        }
    },
    'observation_wells_data': {
        'foreign_constraints': [
            ('sampling_feature_uuid', 'manual_measurements'),
            ('sampling_feature_uuid', 'sonde_installations'),
            ('sampling_feature_uuid', 'repere_data')],
        'columns': {
            'obs_well_id': {
                'dtype': 'str',
                'desc': ("The unique identifier of the observation well.")
            },
            'latitude': {
                'dtype': 'float',
                'desc': ("The latitude of the observation well location "
                         "in decimal degrees.")
            },
            'longitude': {
                'dtype': 'float',
                'desc': ("The longitude of the observation well location "
                         "in decimal degrees.")
            },
            'common_name': {
                'dtype': 'str',
                'desc': ("The human readable name of the well.")
            },
            'municipality': {
                'dtype': 'str',
                'desc': ("The municipality where the well is installed.")
            },
            'aquifer_type': {
                'dtype': 'str',
                'desc': ("Indicates if the well is open in the bedrock or "
                         "in the unconsolidated sediment.")
            },
            'confinement': {
                'dtype': 'str',
                'desc': ("Indicates if the confinement at the well location "
                         "is confined, unconfined or semi-confined.")
            },
            'aquifer_code': {
                'dtype': 'Int64',
                'desc': ("A code that represents the combination of aquifer "
                         "type and confinement for the well.")
            },
            'in_recharge_zone': {
                'dtype': 'str',
                'desc': ("Indicates whether the observation well is located "
                         "in or in the proximity a recharge zone.")
            },
            'is_influenced': {
                'dtype': 'str',
                'desc': ("Indicates whether the water levels measured in "
                         "that well are influenced or not by anthropic "
                         "phenomenon.")
            },
            'elevation': {
                'dtype': 'float',
                'desc': ("The elevation of the ground surface at the "
                         "observation well location in meters above "
                         "sea level.")
            },
            'is_station_active': {
                'dtype': 'bool',
                'desc': ("Indicates whether the station is still "
                         "active or not.")
            },
            'obs_well_notes': {
                'dtype': 'str',
                'desc': ("Any notes related to the observation well.")
            },
        }
    },
    'sonde_models_lib': {
        'foreign_constraints': [
            ('sonde_model_id', 'sondes_data')],
        'columns': {
            'sonde_brand_model': {
                'dtype': 'str',
                'desc': ("A sonde brand and model combination.")
            },
            'sonde_brand': {
                'dtype': 'str',
                'desc': ("A sonde manufacturer.")
            },
            'sonde_model': {
                'dtype': 'str',
                'desc': ("A sonde model.")
            },
        }
    },
}
