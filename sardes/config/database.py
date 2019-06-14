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
try:
    import keyring
except Exception:
    keyring = None

DB_CONNECTION_KEYS = ['database', 'user', 'host']


def get_dbconfig():
    """
    Get and return the database configuration parameters last saved in the
    config file.
    """
    filename = osp.join(get_config_dir(__appname__), 'dbconfig.json')
    if osp.exists(filename):
        with open(filename) as json_file:
            dbconfig = json.load(json_file)
    else:
        dbconfig = {key: '' for key in DB_CONNECTION_KEYS}
    dbconfig['password'] = get_password(dbconfig['database'], dbconfig['user'])

    return dbconfig


def set_dbconfig(**kargs):
    """
    Set the specified database configuration parameters to the database
    configuration file.
    """
    dbconfig = get_dbconfig()
    dbconfig.update(kargs)

    store_password(
        dbconfig['database'], dbconfig['user'], dbconfig['password'])

    # Remove keys that do not belong in our configs.
    dbconfig = {key: value for key, value in dbconfig.items() if
                key in DB_CONNECTION_KEYS}

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


def store_password(database, username, password):
    """Store credentials securely for future use if possible."""
    if keyring is not None and database and username and password:
        try:
            keyring.set_password(
                __appname__, "{}/{}".format(database, username), password)
        except Exception as e:
            print(e)
        else:
            print('Password saved successfully.')


def get_password(database, username):
    """
    Get pasword saved for that database and username or else return an empty
    string.
    """
    if keyring is not None and database and username:
        password = keyring.get_password(
            __appname__, "{}/{}".format(database, username))
        return password or ''
    else:
        return ''
