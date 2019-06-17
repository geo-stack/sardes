# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports
import platform

# ---- Third party imports
from sardes import __appname__, is_frozen
from sardes.config.main import CONF
try:
    import keyring
    if platform.system() == 'Windows' and is_frozen():
        import keyring.backends.Windows
        keyring.set_keyring(keyring.backends.Windows.WinVaultKeyring())
except Exception:
    keyring = None

DB_CONNECTION_KEYS = ['database', 'user', 'host']


def get_dbconfig():
    """
    Get and return the database configuration parameters last saved in the
    config file.
    """
    dbconfig = {}
    for key in DB_CONNECTION_KEYS:
        dbconfig[key] = CONF.get('database', key)
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

    # Save the connection parameters in our configs.
    for key in DB_CONNECTION_KEYS:
        CONF.set('database', key, dbconfig[key])


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
