# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports
import os
import os.path as osp

# ---- Third party imports
from appconfigs.user import UserConfig
from appconfigs.base import get_config_dir

# ---- Local imports
from sardes import __appname__

CONFIG_DIR = get_config_dir(__appname__)
if bool(os.environ.get('SARDES_PYTEST')):
    CONFIG_DIR += '_pytest'

TEMP_DIR = osp.join(CONFIG_DIR, 'Temp')
if not osp.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

DEFAULTS = [
    ('main',
        {'language': 'en',
         'panes_and_toolbars_locked': False
         }
     ),
    ('database',
        {'dbtype_last_selected': 'Sardes SQLite',
         'auto_connect_to_database': False,
         }
     ),
    ('documents_settings',
        {'xlsx_font': 'Calibri',
         'graph_font': 'Arial',
         }
     )
]

# =============================================================================
# Config instance
# =============================================================================
# IMPORTANT NOTES:
# 1. If you want to *change* the default value of a current option, you need to
#    do a MINOR update in config version, e.g. from 3.0.0 to 3.1.0
# 2. If you want to *remove* options that are no longer needed in our codebase,
#    or if you want to *rename* options, then you need to do a MAJOR update in
#    version, e.g. from 3.0.0 to 4.0.0
# 3. You don't need to touch this value if you're just adding a new option
CONF_VERSION = '4.1.1'

# Setup the main configuration instance.
LOAD = False if bool(os.environ.get('SARDES_PYTEST')) else True
try:
    CONF = UserConfig('sardes', defaults=DEFAULTS, load=LOAD,
                      version=CONF_VERSION, path=CONFIG_DIR,
                      backup=True, raw_mode=True)
except Exception:
    CONF = UserConfig('sardes', defaults=DEFAULTS, load=False,
                      version=CONF_VERSION, path=CONFIG_DIR,
                      backup=True, raw_mode=True)
