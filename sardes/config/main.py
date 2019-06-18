# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Third party imports
from appconfigs.user import UserConfig
from appconfigs.base import get_config_dir

# ---- Local imports
from sardes import __appname__

CONFIG_DIR = get_config_dir(__appname__)

DEFAULTS = [
    ('main',
        {'fontsize_global': '14px'}
     ),
    ('database',
        {'database': '',
         'host': '',
         'user': '',
         'port': 5432,
         'encoding': 'utf_8'}
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
CONF_VERSION = '1.0.0'

# Setup the main configuration instance.
try:
    CONF = UserConfig('sardes', defaults=DEFAULTS, load=True,
                      version=CONF_VERSION, path=CONFIG_DIR,
                      backup=True, raw_mode=True)
except Exception:
    CONF = UserConfig('sardes', defaults=DEFAULTS, load=False,
                      version=CONF_VERSION, path=CONFIG_DIR,
                      backup=True, raw_mode=True)
