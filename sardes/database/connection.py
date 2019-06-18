# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Standard imports
import sys

# ---- Third party imports
import psycopg2
from qtpy.QtCore import QObject, Qt, QThread, Signal, Slot
from qtpy.QtWidgets import (QApplication, QAbstractButton, QDialog,
                            QDialogButtonBox, QFormLayout, QGridLayout,
                            QGroupBox, QLabel, QLineEdit, QPushButton,
                            QVBoxLayout, QSpinBox)
from sqlalchemy import create_engine
from sqlalchemy.exc import DBAPIError

# ---- Local imports
from sardes.config.database import get_dbconfig, set_dbconfig
from sardes.config.gui import RED
from sardes.widgets.statusbar import ProcessStatusBar


class PGDatabaseConnector(object):
    """
    This class manage the connection to the database. The default host is the LOCAL_HOST.
    """

    def __init__(self, database: str, user: str, password: str, host: str, port: str):
        """

        :param database:
        :param user:
        :param password:
        """
        self._database_name = database
        self.user = user
        self._password = password
        self._host = host
        self._port = port
        # start Log File
        self._write_start_log_file()
        # create SQL Alchemy engine
        self.db_engine = create_engine(
            "postgresql://{}:{}@{}:{}/{}".format(self.user,
                                                 self._password,
                                                 self._host,
                                                 self._port,
                                                 self._database_name),
            isolation_level="AUTOCOMMIT",
            client_encoding='utf8',
            echo=False)
        # Connect the engine
        self.db_connexion = self.db_engine.connect()
        # set session
        self.session = Session(bind=self.db_engine, autocommit=False)
        self.db_engine.execute('set search_path to public, '
                               'om_metadata,features_observation,'
                               'temp_water_process, om_librairies, '
                               'process, meta_project_management')
        self.inspector = inspect(self.db_engine)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    dialog = DatabaseConnManager()
    dialog.show()
    sys.exit(app.exec_())
