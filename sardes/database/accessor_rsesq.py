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
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker, relationship

# ---- Local imports
from sardes.api.database_accessor import DatabaseAccessorBase
from sardes.database.utils import map_table_column_names, format_sqlobject_repr
from sardes.api.timeseries import TimeSeriesGroup, TimeSeries


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

    sampling_feature_uuid = Column(
        'elemcarac_uuid', UUID(as_uuid=True), primary_key=True)
    interest_id = Column('interet_id', String)
    loc_id = Column(Integer, ForeignKey('rsesq.localisation.loc_id'))

    __mapper_args__ = {'polymorphic_on': interest_id}

    location = relationship("Location", back_populates="sampling_features")

    def __repr__(self):
        return format_sqlobject_repr(self)


class ObservationWell(SamplingFeature):
    """
    An object used to map the observation wells of the RSESQ.
    """
    __mapper_args__ = {'polymorphic_identity': 1}
    obs_well_id = Column('elemcarac_nom', String)
    obs_well_notes = Column('elemcarac_note', String)


class LoggerInstallation(Base):
    __tablename__ = 'sonde_installation'
    __table_args__ = ({"schema": "processus"})

    installation_id = Column('deploiement_id', String, primary_key=True)
    logger_id = Column('no_sonde', String)
    obs_well_id = Column('no_piezometre', String)


class Observation(Base):
    __tablename__ = 'observation'
    __table_args__ = ({"schema": "rsesq"})

    observation_uuid = Column('observation_uuid', String, primary_key=True)
    sampling_feature_uuid = Column('elemcarac_uuid', String)
    process_uuid = Column('process_uuid', String)

    def __repr__(self):
        return format_sqlobject_repr(self)


class ObservationProperty(Base):
    __tablename__ = 'xm_observed_property'
    __table_args__ = ({"schema": "librairies"})

    obs_property_id = Column('obs_property_id', Integer, primary_key=True)
    obs_property_name = Column('observed_property', Integer, primary_key=True)
    obs_property_desc = Column('observed_property_description', String)
    obs_property_units = Column('unit', String)

    def __repr__(self):
        return format_sqlobject_repr(self)


class TimeSeriesChannels(Base):
    __tablename__ = 'canal_temporel'
    __table_args__ = ({"schema": "resultats"})

    channel_uuid = Column('canal_uuid', String, primary_key=True)
    observation_uuid = Column('observation_uuid', String)
    obs_property_id = Column('obs_property_id', Integer)

    def __repr__(self):
        return format_sqlobject_repr(self)


class TimeSeriesRaw(Base):
    __tablename__ = 'temporel_non_corrige'
    __table_args__ = ({"schema": "resultats"})

    raw_temporal_data_uuid = Column(
        'temp_non_cor_uuid', String, primary_key=True)
    channel_uuid = Column('canal_uuid', String)
    datetime = Column('date_temps', DateTime)
    value = Column('valeur', Float)


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

    # ---- Database connection
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

    # ---- Observation wells
    @property
    def observation_wells(self):
        """
        Return the list of observation wells that are saved in the
        database.
        """
        obs_well_ids = (
            self._session.query(ObservationWell.obs_well_id)
            .order_by(ObservationWell.obs_well_id)
            .all()
            )
        return [obj.obs_well_id for obj in obs_well_ids]

    def _get_obs_well_sampling_feature_uuid(self, obs_well_id):
        sampling_feature_uuid = (
            self._session.query(ObservationWell.sampling_feature_uuid)
            .filter(ObservationWell.obs_well_id == obs_well_id)
            .one()
            .sampling_feature_uuid
            )
        return sampling_feature_uuid

    def get_observation_wells_data(self):
        """
        Return a :class:`pandas.DataFrame` containing the information related
        to the observation wells that are saved in the database.
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
            split_notes = obs_wells['obs_well_notes'].str.split(r'\|\|')
            obs_wells.drop(labels='obs_well_notes', axis=1, inplace=True)
            for i, key in enumerate(keys_in_notes):
                obs_wells[key] = (
                    split_notes.str[i].str.split(':').str[1].str.strip())
                obs_wells[key] = obs_wells[key][obs_wells[key] != 'NULL']

            # Convert to bool.
            obs_wells['is_station_active'] = (
                obs_wells['is_station_active']
                .map({'True': True, 'False': False}))

            obs_wells['municipality'] = (
                obs_wells['loc_notes'].str.split(':').str[1].str.strip())

            # Set the index to the observation well ids.
            obs_wells.set_index('obs_well_id', inplace=True, drop=False)
        else:
            obs_wells = pd.DataFrame([])

        return obs_wells

    # ---- Monitored properties
    @property
    def monitored_properties(self):
        """
        Returns the list of properties for which time data is stored in the
        database.
        """
        obs_prop_ids = (
            self._session.query(ObservationProperty.obs_property_name)
            .filter(TimeSeriesChannels.obs_property_id ==
                    ObservationProperty.obs_property_id)
            .distinct(ObservationProperty.obs_property_name)
            .all())
        return [obj.obs_property_name for obj in obs_prop_ids]

    def get_monitored_property_name(self, monitored_property):
        """
        Return the common human readable name for the corresponding
        monitored property.
        """
        return (
            self._session.query(ObservationProperty)
            .filter(ObservationProperty.obs_property_name ==
                    monitored_property)
            .one()
            .obs_property_desc)

    def get_monitored_property_units(self, monitored_property):
        """
        Return the units in which the time data for this monitored property
        are saved in the database.
        """
        return (
            self._session.query(ObservationProperty)
            .filter(ObservationProperty.obs_property_name ==
                    monitored_property)
            .one()
            .obs_property_units)

    def get_monitored_property_color(self, monitored_property):
        return {'NIV_EAU': 'blue',
                'TEMP': 'red',
                'COND_ELEC': 'cyan'
                }[monitored_property]

    # ---- Timeseries
    def get_timeseries_for_obs_well(self, obs_well_id, monitored_property):
        """
        Return a :class:`MonitoredProperty` object containing the
        :class:`TimeSeries` objects holding the data acquired in the
        observation well for the specified monitored property.
        """
        # Get the observation property id that is used to reference in the
        # database the corresponding monitored property.
        obs_property_id = (
            self._session.query(ObservationProperty.obs_property_id)
            .filter(ObservationProperty.obs_property_name ==
                    monitored_property)
            .one()
            .obs_property_id
            )

        # Get the sampling feature uuid corresponding to the observation well.
        sampling_feature_uuid = (
            self._get_obs_well_sampling_feature_uuid(obs_well_id))

        # Define a query to fetch the timseries data from the database.
        query = (
            self._session.query(TimeSeriesRaw.value,
                                TimeSeriesRaw.datetime,
                                TimeSeriesRaw.channel_uuid)
            .filter(Observation.sampling_feature_uuid == sampling_feature_uuid)
            .filter(Observation.observation_uuid ==
                    TimeSeriesChannels.observation_uuid)
            .filter(TimeSeriesChannels.obs_property_id == obs_property_id)
            .filter(TimeSeriesRaw.channel_uuid ==
                    TimeSeriesChannels.channel_uuid)
            .order_by(TimeSeriesRaw.datetime)
            ).with_labels()

        # Fetch the data from the database and store them in a pandas
        # Series using datetimes as index.
        data = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True)
        columns_map = map_table_column_names(
            Observation, TimeSeriesChannels, TimeSeriesRaw, with_labels=True)
        data.rename(columns_map, axis='columns', inplace=True)

        data['datetime'] = pd.to_datetime(
            data['datetime'], format="%Y-%m-%d %H:%M:%S")
        data.set_index(['datetime'], drop=True, inplace=True)

        # For each channel, store the data in a time series object and
        # add it to the monitored property object.
        tseries_group = TimeSeriesGroup(
            monitored_property,
            self.get_monitored_property_name(monitored_property),
            self.get_monitored_property_units(monitored_property)
            )
        for channel_uuid in data['channel_uuid'].unique():
            channel_data = data[data['channel_uuid'] == channel_uuid]
            tseries_group.add_timeseries(TimeSeries(
                pd.Series(channel_data['value'], index=channel_data.index),
                tseries_id=channel_uuid,
                tseries_name=(
                    self.get_monitored_property_name(monitored_property)),
                tseries_units=(
                    self.get_monitored_property_units(monitored_property)),
                tseries_color=(
                    self.get_monitored_property_color(monitored_property))
                ))

        return tseries_group

    def execute(self, sql_request, **kwargs):
        """Execute a SQL statement construct and return a ResultProxy."""
        try:
            return self._connection.execute(sql_request, **kwargs)
        except ProgrammingError as p:
            print("Permission error for user {}".format(self.user))
            raise p


if __name__ == "__main__":
    from sardes.config.database import get_dbconfig

    dbconfig = get_dbconfig('rsesq_postgresql')
    accessor = DatabaseAccessorRSESQ(**dbconfig)

    accessor.connect()
    obs_wells = accessor.get_observation_wells_data()

    print(accessor.observation_wells)
    print(accessor.monitored_properties)
    for monitored_propery in accessor.monitored_properties:
        print(accessor.get_monitored_property_name(monitored_propery))
        print(accessor.get_monitored_property_units(monitored_propery))

    from time import time
    for i in range(5):
        t1 = time()
        print(str(i + 1) + '/10', end='')
        wldata = accessor.get_timeseries_for_obs_well('01370001', 'NIV_EAU')
        t2 = time()
        print(": %0.5f sec" % (t2 - t1))
    accessor.close_connection()
