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
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy import ForeignKey
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker, relationship

# ---- Local imports
from sardes.database.accessor_base import ObservationWell


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
    note = Column('remarque', String)

    sampling_features = relationship(
        "SamplingFeature", back_populates="location")

    def __repr__(self):
        returned_value = "<Location("
        for attr in self.__mapper_args__['include_properties']:
            returned_value += "{}={} ".format(attr, getattr(self, attr))
        returned_value += ")>"
        return returned_value


class SamplingFeature(Base):
    """
    An object used to map the 'elements_caracteristique' table of the
    RSESQ database.
    """
    __tablename__ = 'elements_caracteristique'
    __table_args__ = ({"schema": "rsesq"})

    sampling_feature_id = Column('elemcarac_id', Integer, primary_key=True)
    sampling_feature_uuid = Column('elemcarac_uuid', String)
    sampling_feature_name = Column('elemcarac_nom', String)
    sampling_feature_note = Column('elemcarac_note', String)
    interest_id = Column('interet_id', String)
    loc_id = Column(Integer, ForeignKey('rsesq.localisation.loc_id'))

    __mapper_args__ = {
        'include_properties': [
            'sampling_feature_id',
            'sampling_feature_uuid',
            'sampling_feature_name',
            'sampling_feature_note',
            'loc_id',
            'interest_id']}

    location = relationship(
        "Location", back_populates="sampling_features")

    def __repr__(self):
        returned_value = "<SamplingFeature("
        for attr in self.__mapper_args__['include_properties']:
            returned_value += "{}={} ".format(attr, getattr(self, attr))
        returned_value += ")>"
        return returned_value


# =============================================================================
# ---- Accessor
# =============================================================================
class DatabaseAccessorRSESQ(object):
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
        self._connection = None
        self._connection_error = None
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
            sampling_features = (
                self._session.query(SamplingFeature)
                .order_by(SamplingFeature.sampling_feature_name)
                .filter(SamplingFeature.interest_id == 1)
                .all())
            obs_wells = []
            for sampling_feature in sampling_features:
                notes = (sampling_feature.sampling_feature_note
                         .replace('NULL', '')
                         .split('||'))
                obs_wells.append(ObservationWell(
                    no_well=sampling_feature.sampling_feature_name,
                    common_name=notes[0].split(':')[1].strip(),
                    municipality=(
                        sampling_feature.location.note.split(':')[1].strip()),
                    aquifer_type=notes[1].split(':')[1].strip(),
                    aquifer_code=notes[3].split(':')[1].strip(),
                    confinement=notes[2].split(':')[1].strip(),
                    in_recharge_zone=notes[4].split(':')[1].strip(),
                    is_influenced=notes[5].split(':')[1].strip(),
                    is_station_active=notes[6].split(':')[1].strip() == 'True',
                    latitude=sampling_feature.location.latitude,
                    longitude=sampling_feature.location.longitude,
                    elevation=None,
                    note=notes[7].split(':')[1].strip()
                    ))
            return obs_wells
        else:
            return []

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
    print(accessor._connection, accessor._connection_error)

    obs_wells = accessor.get_observation_wells()
    accessor.close_connection()
