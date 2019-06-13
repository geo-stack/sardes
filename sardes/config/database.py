# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports
import json
import os.path as osp

# ---- Third party imports
from appconfigs.base import get_config_dir
from sardes import __appname__


def get_dbconfig():
    """
    Get and return the database configuration parameters last saved in the
    config file.
    """
    filename = osp.join(get_config_dir(__appname__), 'dbconfig.json')
    if osp.exists(filename):
        with open(filename) as json_file:
            dbconfig = json.load(json_file)
        return dbconfig
    else:
        return {}
