# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Object-Relational Mapping and Accessor implementation of the RSESQ database.
"""

# ---- Third party imports
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy import ForeignKey
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker, relationship

# ---- Local imports
from sardes.database.utils import map_table_column_names, format_sqlobject_repr
from sardes.api.database_accessor import DatabaseAccessorBase


# =============================================================================
# ---- Object-Relational Mapping
# =============================================================================
Base = declarative_base()


class Location(Base):
    """
    An object used to map the 'Localisation' table of the RSESQ database.
    """
    __tablename__ = 'localisation'
    __table_args__ = ({"schema": "rsesq"})
    __mapper_args__ = {
        'include_properties': [
            'loc_id', 'latitude', 'longitude', 'note']}

    loc_id = Column(String, primary_key=True)
    latitude = Column('latitude_8', Float)
    longitude = Column(Float)
    is_station_active = Column('station_active', String)
    loc_notes = Column('remarque', String)

    sampling_features = relationship(
        "SamplingFeature", back_populates="location")

    def __repr__(self):
        return format_sqlobject_repr(self)


class SamplingFeature(Base):
    """
    An object used to map the 'elements_caracteristique' table of the
    RSESQ database.
    """
    __tablename__ = 'elements_caracteristique'
    __table_args__ = ({"schema": "rsesq"})

    sampling_feature_uuid = Column('elemcarac_uuid', String, primary_key=True)
    interest_id = Column('interet_id', String)
    loc_id = Column(Integer, ForeignKey('rsesq.localisation.loc_id'))

    __mapper_args__ = {'polymorphic_on': interest_id}

    location = relationship(
        "Location", back_populates="sampling_features")

    def __repr__(self):
        return format_sqlobject_repr(self)


class ObservationWell(SamplingFeature):
    """
    An object used to map the observation wells of the RSESQ.
    """
    __mapper_args__ = {'polymorphic_identity': 1}
    obs_well_id = Column('elemcarac_nom', String)
    obs_well_notes = Column('elemcarac_note', String)


# =============================================================================
# ---- Accessor
# =============================================================================
class DatabaseAccessorRSESQ(DatabaseAccessorBase):
    """
    Manage the connection and requests to a RSESQ database.
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
        self._engine = self._create_engine()

        # create a session.
        Session = sessionmaker(bind=self._engine)
        self._session = Session()

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

    def get_observation_wells(self):
        """
        Get the list of observations wells that are saved in the database.
        """
        if self.is_connected():
            query = (
                self._session.query(ObservationWell,
                                    Location.latitude,
                                    Location.longitude,
                                    Location.loc_notes)
                .filter(Location.loc_id == ObservationWell.loc_id)
                .order_by(ObservationWell.obs_well_id)
                ).with_labels()
            obs_wells = pd.read_sql_query(
                query.statement, query.session.bind, coerce_float=True)

            # Rename the column names to that expected by the api.
            columns_map = map_table_column_names(
                Location, ObservationWell, with_labels=True)
            obs_wells.rename(columns_map, axis='columns', inplace=True)

            # Reformat notes correctly.
            keys_in_notes = ['common_name', 'aquifer_type', 'confinement',
                             'aquifer_code', 'in_recharge_zone',
                             'is_influenced', 'is_station_active',
                             'obs_well_notes']
            split_notes = obs_wells['obs_well_notes'].str.split('\|\|')
            obs_wells.drop(labels='obs_well_notes', axis=1, inplace=True)
            for i, key in enumerate(keys_in_notes):
                obs_wells[key] = (
                    split_notes.str[i].str.split(':').str[1].str.strip())
                obs_wells[key] = obs_wells[key][obs_wells[key] != 'NULL']

            obs_wells['municipality'] = (
                obs_wells['loc_notes'].str.split(':').str[1].str.strip())

            return obs_wells
        else:
            return pd.DataFrame([])

    def get_observations(self):
        pass
        # observation

    def execute(self, sql_request, **kwargs):
        """Execute a SQL statement construct and return a ResultProxy."""
        try:
            return self._connection.execute(sql_request, **kwargs)
        except ProgrammingError as p:
            print("Permission error for user {}".format(self.user))
            raise p


if __name__ == "__main__":
    from sardes.config.database import get_dbconfig
    dbconfig = get_dbconfig()
    accessor = DatabaseAccessorRSESQ(
        'rsesq', 'rsesq', '((Rsesq2019', '198.73.161.237', 5432)

    accessor.connect()
    obs_wells = accessor.get_observation_wells()
    accessor.close_connection()
