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
    if is_frozen():
        # This woraround is required for keyring to work when the
        # application is frozen with pyinstaller. See jaraco/keyring#324.
        if platform.system() == 'Windows':
            import keyring.backends.Windows
            keyring.set_keyring(keyring.backends.Windows.WinVaultKeyring())
except Exception:
    keyring = None


def get_dbconfig(dbtype_name):
    """
    Get and return the database configuration parameters last saved in the
    config file.
    """
    dbtype_name = dbtype_name.lower().replace(' ', '_')
    dbconfig = CONF.get('database', 'dbtype/' + dbtype_name, {})
    dbconfig['password'] = get_password(dbtype_name)

    return dbconfig


def set_dbconfig(dbtype_name, dbconfig):
    """
    Set the specified database configuration parameters to the database
    configuration file.
    """
    dbtype_name = dbtype_name.lower().replace(' ', '_')

    # Store credentials securely for future use if possible.
    if 'password' in dbconfig:
        store_password(dbtype_name, dbconfig['password'])
        del dbconfig['password']

    # Save the connection parameters in our configs.
    CONF.set('database', 'dbtype/' + dbtype_name, dbconfig)


def store_password(dbtype_name, password):
    """Store credentials securely for future use if possible."""
    if keyring is not None and dbtype_name and password:
        dbtype_name = dbtype_name.lower().replace(' ', '_')
        try:
            keyring.set_password(__appname__, dbtype_name, password)
        except Exception as e:
            print(e)


def get_password(dbtype_name):
    """
    Get password saved for that database type or else return an empty string.
    """
    password = ''
    if keyring is not None and dbtype_name:
        dbtype_name = dbtype_name.lower().replace(' ', '_')
        try:
            password = keyring.get_password(__appname__, dbtype_name)
        except RuntimeError:
            pass
    return password or ''
