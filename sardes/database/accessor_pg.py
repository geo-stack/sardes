# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports
import os.path as osp
# ---- Third party imports
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker

# ---- Local imports
from sardes.config.main import CONFIG_DIR


PATH_DB_LOGFILE = osp.join(CONFIG_DIR, 'database_log.txt')


Base = declarative_base()

LOCTABLEATTRS = [
    'no_piezometre', 'nom_communn', 'municipalite', 'aquifere',
    'nappe', 'code_aqui', 'zone_rechar', 'influences', 'latitude_8',
    'longitude', 'station_active', 'remarque', 'loc_id', 'geom'
    ]


class Location(Base):
    """
    An object used to map the 'Localisation'table of the database.
    """

    __tablename__ = 'localisation'
    no_piezometre = Column(String)
    nom_communn = Column(String)
    municipalite = Column(String)
    aquifere = Column(String)
    nappe = Column(String)
    code_aqui = Column(Integer)
    zone_rechar = Column(String)
    influences = Column(String)
    latitude_8 = Column(Float)
    longitude = Column(Float)
    station_active = Column(String)
    remarque = Column(String)
    loc_id = Column(String, primary_key=True)
    geom = Column(String)

    def __repr__(self):
        returned_value = "<Location("
        for attr in LOCTABLEATTRS:
            returned_value += "{}={}".format(attr, getattr(self, attr))
        returned_value += ")>"
        return returned_value


class DataAccessorPG(object):
    """
    Manage the connection and requests to a PostgreSQL database.
    """

    def __init__(self, database, username, password, hostname, port,
                 client_encoding='utf8'):
        self._database = database
        self._username = username
        self._password = password
        self._hostname = hostname
        self._port = port
        self._client_encoding = client_encoding

        # create a SQL Alchemy engine.
        self._connection = None
        self._connection_error = None
        self._engine = self._create_engine()

        # create a session.
        Session = sessionmaker(bind=self._engine)
        self._session = Session()

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

    def is_connected(self):
        """Return whether a connection to a database is currently active."""
        if self._connection is None:
            return False
        else:
            return not self._connection.closed

    def connect(self):
        """
        Create a new connection object to communicate with the database.
        """
        try:
            self._connection = self._engine.connect()
        except DBAPIError as e:
            self._connection = None
            self._connection_error = e
        else:
            self._connection_error = None

    def close_connection(self):
        """
        Close the current connection with the database.
        """
        self._engine.dispose()
        self._connection = None

    def get_locations(self, sort=True):
        """
        Get the content of the locations table from the database.
        """
        if self.is_connected():
            if sort:
                locations = self._session.query(Location).order_by(
                     Location.no_piezometre).all()
            else:
                locations = self._session.query(Location).all()
            return locations
        else:
            return []

    def execute(self, sql_request, **kwargs):
        """Execute a SQL statement construct and return a ResultProxy."""
        try:
            return self._connection.execute(sql_request, **kwargs)
        except ProgrammingError as p:
            print("Permission error for user {}".format(self.user))
            raise p
