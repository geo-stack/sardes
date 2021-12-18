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
                'type': 'object',
                'desc': ("A unique identifier that is used to reference the "
                         "observation well in the database in which the "
                         "manual measurement was made."),
            },
            'datetime': {
                'type': 'datetime64[ns]',
                'desc': ("A datetime object corresponding to the date and "
                         "time when the manual measurement was made in the "
                         "well.")
            },
            'value': {
                'type': 'float64',
                'desc': ("The value of the water level that was measured "
                         "manually in the well.")
            },
            'notes': {
                'type': 'str',
                'desc': ("Any notes related to the manual measurement.")
            }
        }
    },
    'sonde_installations': {
        'foreign_constraints': [],
        'columns': {
            'sampling_feature_uuid': {
                'type': 'object',
                'desc': ("A unique identifier that is used to reference the "
                         "observation well in which the sonde are installed.")
            },
            'sonde_uuid': {
                'type': 'object',
                'desc': ("A unique identifier used to reference each sonde in "
                         "the database.")
            },
            'start_date': {
                'type': 'datetime64[ns]',
                'desc': ("The date and time at which the sonde was installed "
                         "in the well.")
            },
            'end_date': {
                'type': 'datetime64[ns]',
                'desc': ("The date and time at which the sonde was removed "
                         "from the well.")
            },
            'install_depth': {
                'type': 'float',
                'desc': ("The depth at which the sonde was installed in "
                         "the well.")
            }
        }
    },
    'repere_data': {
        'foreign_constraints': [],
        'columns': {
            'sampling_feature_uuid': {
                'type': 'object',
                'desc': ("A unique identifier that is used to reference the "
                         "observation well for which the repere data are "
                         "associated.")
            },
            'top_casing_alt': {
                'type': 'float',
                'desc': ("The altitude values given in meters of the top of "
                         "the observation wells' casing.")
            },
            'casing_length': {
                'type': 'float',
                'desc': ("The lenght of the casing above ground level "
                         "given in meters.")
            },
            'start_date': {
                'type': 'datetime64[ns]',
                'desc': ("The date and time after which repere data "
                         "are valid.")
            },
            'end_date': {
                'type': 'datetime64[ns]',
                'desc': ("The date and time before which repere data "
                         "are valid.")
            },
            'is_alt_geodesic': {
                'type': 'bool',
                'desc': ("Whether the top_casing_alt value is geodesic.")
            },
            'repere_note': {
                'type': 'str',
                'desc': ("Any note related to the repere data.")
            },
        }
    },
    'sondes_data': {
        'foreign_constraints': [
            ('sonde_uuid', 'sonde_installations')],
        'columns': {
            'sonde_serial_no': {
                'type': 'str',
                'desc': ("The serial number of the sonde.")
            },
            'sonde_model_id': {
                'type': 'object',
                'desc': ("The ID used to reference the sonde brand and model "
                         "in the database.")
            },
            'date_reception': {
                'type': 'datetime64[ns]',
                'desc': ("The date when the sonde was added to the inventory.")
            },
            'date_withdrawal': {
                'type': 'datetime64[ns]',
                'desc': ("The date when the sonde was removed from the "
                         "inventory.")
            },
            'in_repair': {
                'type': 'bool',
                'desc': ("Indicate wheter the sonde is currently being "
                         "repaired.")
            },
            'out_of_order': {
                'type': 'bool',
                'desc': ("Indicate whether the sonde is out of order. "
                         "unconsolidated sediment.")
            },
            'lost': {
                'type': 'bool',
                'desc': ("Indicates whether the sonde has been lost.")
            },
            'off_network': {
                'type': 'bool',
                'desc': ("Indicate whether the sonde is currently being used "
                         "outside of the monitoring network.")
            },
            'sonde_notes': {
                'type': 'str',
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
                'type': 'str',
                'desc': ("The unique identifier of the observation well.")
            },
            'latitude': {
                'type': 'float',
                'desc': ("The latitude of the observation well location "
                         "in decimal degrees.")
            },
            'longitude': {
                'type': 'float',
                'desc': ("The longitude of the observation well location "
                         "in decimal degrees.")
            },
            'common_name': {
                'type': 'str',
                'desc': ("The human readable name of the well.")
            },
            'municipality': {
                'type': 'str',
                'desc': ("The municipality where the well is installed.")
            },
            'aquifer_type': {
                'type': 'str',
                'desc': ("Indicates if the well is open in the bedrock or "
                         "in the unconsolidated sediment.")
            },
            'confinement': {
                'type': 'str',
                'desc': ("Indicates if the confinement at the well location "
                         "is confined, unconfined or semi-confined.")
            },
            'aquifer_code': {
                'type': 'Int64',
                'desc': ("A code that represents the combination of aquifer "
                         "type and confinement for the well.")
            },
            'in_recharge_zone': {
                'type': 'str',
                'desc': ("Indicates whether the observation well is located "
                         "in or in the proximity a recharge zone.")
            },
            'is_influenced': {
                'type': 'str',
                'desc': ("Indicates whether the water levels measured in "
                         "that well are influenced or not by anthropic "
                         "phenomenon.")
            },
            'elevation': {
                'type': 'float',
                'desc': ("The elevation of the ground surface at the "
                         "observation well location in meters above "
                         "sea level.")
            },
            'is_station_active': {
                'type': 'bool',
                'desc': ("Indicates whether the station is still "
                         "active or not.")
            },
            'obs_well_notes': {
                'type': 'str',
                'desc': ("Any notes related to the observation well.")
            },
        }
    },
    'sonde_models_lib': {
        'foreign_constraints': [
            ('sonde_model_id', 'sondes_data')],
        'columns': {
            'sonde_brand_model': {
                'type': 'str',
                'desc': ("A sonde brand and model combination.")
            },
            'sonde_brand': {
                'type': 'str',
                'desc': ("A sonde manufacturer.")
            },
            'sonde_model': {
                'type': 'str',
                'desc': ("A sonde model.")
            },
        }
    },
}
