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
import os
import os.path as osp
import time

# ---- Third party imports
from appconfigs.base import get_config_dir
from sardes import __appname__

DB_CONNECTION_KEYS = ['dbname', 'user', 'host', 'password']


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


def set_dbconfig(**kargs):
    """
    Set the specified database configuration parameters to the database
    configuration file.
    """
    dbconfig = get_dbconfig()
    dbconfig.update({key: value for key, value in kargs.items() if
                     key in DB_CONNECTION_KEYS})

    filename = osp.join(get_config_dir(__appname__), 'dbconfig.json')
    try:
        with open(filename, 'w', encoding='utf-8') as json_file:
            json.dump(dbconfig, json_file)
    except EnvironmentError:
        try:
            # Try removing the json dbconfig file from the disk.
            if osp.isfile(filename):
                os.remove(filename)
            time.sleep(0.05)
            with open(filename, 'w', encoding='utf-8') as json_file:
                json.dump(dbconfig, json_file)
        except Exception as e:
            print("Failed to write database configuration file to disk, with "
                  "the exception shown below.")
            print(e)
