# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports
from datetime import datetime
import os.path as osp
import sys
import urllib.parse

# ---- Third party imports
from sqlalchemy import create_engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.engine.url import URL

# ---- Local imports
from sardes.config.main import CONFIG_DIR

PATH_DB_LOGFILE = osp.join(CONFIG_DIR, 'database_log.txt')


class PGDatabaseConnManager(object):
    """
    Manage the connection to the database. The default host is the LOCAL_HOST.
    """

    def __init__(self, database, username, password, hostname, port,
                 client_encoding='utf8'):
        self._database = database
        self._username = user
        self._password = password
        self._hostname = host
        self._port = port
        self._client_encoding = client_encoding

        # create a SQL Alchemy engine.
        self._conn = None
        self._engine = self._create_engine()

        # self.inspector = inspect(self._engine)

    def _create_engine(self):
        """Create a SQL Alchemy engine."""
        database_url = URL('postgresql',
                           username=self._username,
                           password=self._password,
                           host=self._hostname,
                           port=self._port,
                           database=self._database)

        return create_engine(database_url,
                             isolation_level="AUTOCOMMIT",
                             client_encoding=self._client_encoding,
                             echo=False)


    def connect(self):
        """
        Create a new connection object in order to communicate with
        the database.
        """
        try:
            self._connection = self._engine.connect()
        except DBAPIError as e:
            self._connection = None
            self._connection_error = e
        else:
            self._connection_error = None
        self._engine.dispose()
        self.session.close_all()



if __name__ == '__main__':
    pass
