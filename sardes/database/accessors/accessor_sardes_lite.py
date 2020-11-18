# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Object-Relational Mapping and Accessor implementation of the Sardes database.
"""

# ---- Standard imports
import os.path as osp
import sqlite3
import uuid

# ---- Third party imports
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, extract, func, and_
from sqlalchemy import (Column, DateTime, Float, ForeignKey, Integer, String,
                        UniqueConstraint, Index)
from sqlalchemy.exc import DBAPIError, ProgrammingError, OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import TEXT, VARCHAR, Boolean
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.engine.url import URL
from sqlalchemy_utils import UUIDType
from sqlalchemy.orm.exc import NoResultFound

# ---- Local imports
from sardes.config.locale import _
from sardes.api.database_accessor import DatabaseAccessor
from sardes.database.utils import format_sqlobject_repr
from sardes.api.timeseries import DataType

# An application ID to help recognize that database files are
# specific to the current accessor.
APPLICATION_ID = 1013042054

# The latest version of the database schema.
CURRENT_SCHEMA_VERSION = 1


# =============================================================================
# ---- Register Adapters
# =============================================================================
# This is required to avoid a "can't adapt type 'numpy.int64' or
# 'numpy.float64'" psycopg2.ProgrammingError.
# See https://stackoverflow.com/questions/50626058

def addapt_numpy_float64(numpy_float64):
    return float(numpy_float64)


def addapt_numpy_int64(numpy_int64):
    return int(numpy_int64)


sqlite3.register_adapter(np.int64, addapt_numpy_int64)
sqlite3.register_adapter(np.float64, addapt_numpy_float64)


# =============================================================================
# ---- Object-Relational Mapping
# =============================================================================
Base = declarative_base()


class BaseMixin(object):
    def __repr__(self):
        return format_sqlobject_repr(self)

    @classmethod
    def initial_attrs(cls):
        """
        This needs to be reimplemented for tables for which we need to add
        default values after creation.
        """
        return []


class Location(BaseMixin, Base):
    """
    An object used to map the 'location' table.
    """
    __tablename__ = 'location'
    __table_args__ = {'sqlite_autoincrement': True}

    loc_id = Column(Integer, primary_key=True)
    latitude = Column(Float)
    longitude = Column(Float)
    municipality = Column(String)


class Repere(BaseMixin, Base):
    """
    An object used to map the 'repere' table.
    """
    __tablename__ = 'repere'

    repere_uuid = Column(UUIDType(binary=False), primary_key=True)
    top_casing_alt = Column(Float)
    casing_length = Column(Float)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    is_alt_geodesic = Column(Boolean)
    repere_note = Column(String(250))
    sampling_feature_uuid = Column(
        UUIDType(binary=False),
        ForeignKey('sampling_feature.sampling_feature_uuid'))


class SamplingFeature(BaseMixin, Base):
    """
    An object used to map the 'sampling_feature' table.
    """
    __tablename__ = 'sampling_feature'

    sampling_feature_uuid = Column(UUIDType(binary=False), primary_key=True)
    sampling_feature_name = Column(String)
    sampling_feature_notes = Column(String)
    loc_id = Column(Integer, ForeignKey('location.loc_id'))
    sampling_feature_type_id = Column(
        Integer, ForeignKey('sampling_feature_type.sampling_feature_type_id'))

    _metadata = relationship(
        "SamplingFeatureMetadata", uselist=False,
        back_populates="sampling_feature")


class SamplingFeatureType(BaseMixin, Base):
    """
    An object used to map the 'sampling_feature_type' library.
    """
    __tablename__ = 'sampling_feature_type'
    __table_args__ = {'sqlite_autoincrement': True}

    sampling_feature_type_id = Column(Integer, primary_key=True)
    sampling_feature_type_desc = Column(String)
    sampling_feature_type_abb = Column(String)


class SamplingFeatureMetadata(BaseMixin, Base):
    """
    An object used to map the 'sampling_feature_metadata' table.
    """
    __tablename__ = 'sampling_feature_metadata'

    sampling_feature_uuid = Column(
        UUIDType(binary=False),
        ForeignKey('sampling_feature.sampling_feature_uuid'),
        primary_key=True)
    in_recharge_zone = Column(String)
    aquifer_type = Column(String)
    confinement = Column(String)
    common_name = Column(String)
    aquifer_code = Column(Integer)
    is_station_active = Column(Boolean)
    is_influenced = Column(String)

    sampling_feature = relationship(
        "SamplingFeature", uselist=False, back_populates="_metadata")


class SamplingFeatureDataOverview(BaseMixin, Base):
    """
    An object used to map the 'sampling_feature_data_overview' table. This
    table contains summary information regarding the water level data that
    are available for each well of the monitoring network.

    Since calculating the content of this table can take several seconds, we
    are caching the results in this table and update its content only when
    needed.
    """
    __tablename__ = 'sampling_feature_data_overview'

    sampling_feature_uuid = Column(
        UUIDType(binary=False),
        ForeignKey('sampling_feature.sampling_feature_uuid'),
        primary_key=True)
    last_date = Column(DateTime)
    first_date = Column(DateTime)
    mean_water_level = Column(Float)


# ---- Observations
class Observation(BaseMixin, Base):
    """
    An object used to map the 'observation' table.
    """
    __tablename__ = 'observation'
    __table_args__ = {'sqlite_autoincrement': True}

    observation_id = Column(Integer, primary_key=True)
    obs_datetime = Column(DateTime)
    sampling_feature_uuid = Column(
        UUIDType(binary=False),
        ForeignKey('sampling_feature.sampling_feature_uuid'))
    process_id = Column(Integer, ForeignKey('process.process_id'))
    obs_type_id = Column(Integer, ForeignKey('observation_type.obs_type_id'))


class ObservationType(BaseMixin, Base):
    """
    An object used to map the 'observation_type' library.
    """
    __tablename__ = 'observation_type'
    __table_args__ = {'sqlite_autoincrement': True}

    obs_type_id = Column(Integer, primary_key=True)
    obs_type_abb = Column(String)
    obs_type_desc = Column(String)


class ObservedProperty(BaseMixin, Base):
    """
    An object used to map the 'observed_property' library.
    """
    __tablename__ = 'observed_property'

    obs_property_id = Column(Integer, primary_key=True)
    obs_property_name = Column('observed_property', Integer)
    obs_property_desc = Column('observed_property_description', String)
    obs_property_units = Column('unit', String)


# ---- Numerical Data
class TimeSeriesChannel(BaseMixin, Base):
    """
    An object used to map the 'timeseries_channel' table.
    """
    __tablename__ = 'timeseries_channel'
    __table_args__ = {'sqlite_autoincrement': True}

    channel_id = Column(Integer, primary_key=True)
    observation_id = Column(
        Integer, ForeignKey('observation.observation_id'))
    obs_property_id = Column(
        Integer, ForeignKey('observed_property.obs_property_id'))


class TimeSeriesData(BaseMixin, Base):
    """
    An object used to map the 'timeseries_data' table.
    """
    __tablename__ = 'timeseries_data'

    datetime = Column(DateTime, primary_key=True, index=True)
    value = Column(Float)
    channel_id = Column(
        Integer, ForeignKey('timeseries_channel.channel_id'),
        primary_key=True, index=True)


class GenericNumericalData(BaseMixin, Base):
    """
    An object used to map the 'generique'.
    """
    __tablename__ = 'generic_numerial_data'

    gen_num_value_uuid = Column(UUIDType(binary=False), primary_key=True)
    gen_num_value = Column(Float)
    observation_id = Column(
        Integer, ForeignKey('observation.observation_id'))
    obs_property_id = Column(
        Integer, ForeignKey('observed_property.obs_property_id'))
    gen_num_value_notes = Column(String)
    gen_init_num_value = Column(String)


# ---- Sondes
class SondeFeature(BaseMixin, Base):
    """
    An object used to map the 'sonde_feature' table.
    """
    __tablename__ = 'sonde_feature'

    sonde_uuid = Column(UUIDType(binary=False), primary_key=True)
    sonde_serial_no = Column(String)
    date_reception = Column(DateTime)
    date_withdrawal = Column(DateTime)
    sonde_model_id = Column(Integer, ForeignKey('sonde_model.sonde_model_id'))
    in_repair = Column(Boolean)
    out_of_order = Column(Boolean)
    lost = Column(Boolean)
    off_network = Column(Boolean)
    sonde_notes = Column(String)


class SondeModel(BaseMixin, Base):
    """
    An object used to map the 'sonde_model' library.
    """
    __tablename__ = 'sonde_model'

    sonde_model_id = Column(Integer, primary_key=True)
    sonde_brand = Column(String)
    sonde_model = Column(String)

    @classmethod
    def initial_attrs(cls):
        return [
            {'sonde_brand': 'Solinst', 'sonde_model': 'LT M10 Gold'},
            {'sonde_brand': 'Solinst', 'sonde_model': 'Barologger M1.5 Gold'},
            {'sonde_brand': 'Solinst', 'sonde_model': 'LT M20 Gold'},
            {'sonde_brand': 'Solinst', 'sonde_model': 'LT M10'},
            {'sonde_brand': 'Solinst', 'sonde_model': 'Barologger M1.5'},
            {'sonde_brand': 'Solinst', 'sonde_model': 'LTC'},
            {'sonde_brand': 'Solinst', 'sonde_model': 'LT M20'},
            {'sonde_brand': 'Solinst', 'sonde_model': 'LTC F30/M10'},
            {'sonde_brand': 'Solinst', 'sonde_model': 'LTC F100/M30'},
            {'sonde_brand': 'Solinst', 'sonde_model': 'LTC M200 Edge'},
            {'sonde_brand': 'Solinst', 'sonde_model': 'LTC M20 Edge'},
            {'sonde_brand': 'Solinst', 'sonde_model': 'LTC M30 Edge'},
            {'sonde_brand': 'Solinst', 'sonde_model': 'LTC M100 Edge'},
            {'sonde_brand': 'Solinst', 'sonde_model': 'LTC M10 Edge'},
            {'sonde_brand': 'Solinst', 'sonde_model': 'LT M10 Edge'},
            {'sonde_brand': 'Solinst', 'sonde_model': 'LT M20 Edge'},
            {'sonde_brand': 'Solinst', 'sonde_model': 'LT M100 Edge'},
            {'sonde_brand': 'Solinst', 'sonde_model': 'L M5'},
            {'sonde_brand': 'Solinst', 'sonde_model': 'LT M5'},
            {'sonde_brand': 'Solinst', 'sonde_model': 'LT M100'},
            {'sonde_brand': 'Solinst', 'sonde_model': 'L M10'},
            {'sonde_brand': 'Solinst', 'sonde_model': 'LT M30'},
            {'sonde_brand': 'Solinst', 'sonde_model': 'LTC Jr'}]


class SondeInstallation(BaseMixin, Base):
    """
    An object used to map the 'sonde_installation' table.
    """
    __tablename__ = 'sonde_installation'
    install_uuid = Column(UUIDType(binary=False), primary_key=True)
    sonde_uuid = Column(
        UUIDType(binary=False), ForeignKey('sonde_feature.sonde_uuid'))
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    install_depth = Column(Float)
    operator = Column(String)
    install_note = Column(String)
    process_id = Column(Integer, ForeignKey('process.process_id'))


# ---- Pompes
class PumpType(BaseMixin, Base):
    """
    An object used to map the 'pump_type' library.
    """
    __tablename__ = 'pump_type'
    pump_type_id = Column(Integer, primary_key=True)
    pump_type_abb = Column(String)
    pump_type_desc = Column(String)


class PumpInstallation(BaseMixin, Base):
    """
    An object used to map the 'pump_installation' table.
    """
    __tablename__ = 'pump_installation'
    install_uuid = Column(UUIDType(binary=False), primary_key=True)
    pump_type_id = Column(Integer, ForeignKey('pump_type.pump_type_id'))
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    install_depth = Column(Float)
    operator = Column(String)
    install_note = Column(String)
    process_id = Column(Integer, ForeignKey('process.process_id'))


# ---- Processes
class Process(BaseMixin, Base):
    """
    An object used to map the 'process' table.
    """
    __tablename__ = 'process'
    __table_args__ = {'sqlite_autoincrement': True}

    process_id = Column(Integer, primary_key=True)
    process_type = Column(String)
    sampling_feature_uuid = Column(
        UUIDType(binary=False),
        ForeignKey('sampling_feature.sampling_feature_uuid'))


# =============================================================================
# ---- Accessor
# =============================================================================
class DatabaseAccessorSardesLite(DatabaseAccessor):
    """
    Manage the connection and requests to a RSESQ database.
    """

    def __init__(self, database, *args, **kargs):
        super().__init__()
        self._database = database

        # create a SQL Alchemy engine.
        self._engine = self._create_engine()

        # create a session.
        Session = sessionmaker(bind=self._engine)
        self._session = Session()

    def execute(self, sql_request, **kwargs):
        """Execute a SQL statement construct and return a ResultProxy."""
        try:
            return self._engine.execute(sql_request, **kwargs)
        except ProgrammingError as p:
            print(p)
            raise p

    def _create_index(self, name):
        """
        Return a new index that can be used subsequently to add a new item
        related to name in the database.
        """
        if name == 'sonde_models_lib':
            try:
                max_commited_id = (
                    self._session.query(func.max(SondeModel.sonde_model_id))
                    .one())[0]
            except TypeError:
                max_commited_id = 0
            return max(self.temp_indexes(name) + [max_commited_id]) + 1
        else:
            return uuid.uuid4()

    # ---- Database setup
    def init_database(self):
        """
        Initialize the tables and attributes of a new database.
        """
        tables = [Location, SamplingFeatureType, SamplingFeature,
                  SamplingFeatureMetadata, SamplingFeatureDataOverview,
                  SondeFeature, SondeModel, SondeInstallation, Process, Repere,
                  ObservationType, Observation, ObservedProperty,
                  GenericNumericalData, TimeSeriesChannel,
                  TimeSeriesData, PumpType, PumpInstallation]
        dialect = self._engine.dialect
        for table in tables:
            if dialect.has_table(self._session, table.__tablename__):
                continue
            Base.metadata.create_all(self._engine, tables=[table.__table__])
            for item_attrs in table.initial_attrs():
                self._session.add(table(**item_attrs))
            self._session.commit()
        self._session.commit()

        self.execute("PRAGMA application_id = {}".format(APPLICATION_ID))
        self.execute("PRAGMA user_version = {}".format(CURRENT_SCHEMA_VERSION))

    # ---- Database connection
    def _create_engine(self):
        """Create a SQL Alchemy engine."""
        database_url = URL('sqlite', database=self._database)
        return create_engine(database_url, echo=False,
                             connect_args={'check_same_thread': False})

    def is_connected(self):
        """Return whether a connection to a database is currently active."""
        return self._connection is not None

    def _connect(self):
        """
        Create a new connection object to communicate with the database.
        """
        if not osp.exists(self._database):
            self._connection = None
            self._connection_error = IOError(_(
                "'{}' does not exist.").format(self._database))
            return
        root, ext = osp.splitext(self._database)
        if ext != '.db':
            self._connection = None
            self._connection_error = IOError(_(
                "'{}' is not a valid database file.").format(self._database))
            return

        # We only test that a connection can be made correctly with the
        # database, but we do not keep a reference to that connection.
        # We let sqlalchemy handle the connection to the database.
        # It is safer to do this to avoid potential problems that could
        # occur due to sharing a same connection across multiple thread.
        # See https://stackoverflow.com/questions/48218065
        # See https://docs.python.org/3/library/sqlite3.html
        try:
            conn = self._engine.connect()
        except DBAPIError as e:
            self._connection = None
            self._connection_error = e
        else:
            app_id = conn.execute("PRAGMA application_id").first()[0]
            version = conn.execute("PRAGMA user_version").first()[0]
            if app_id != APPLICATION_ID:
                self._connection = None
                self._connection_error = sqlite3.DatabaseError(_(
                    "'{}' does not appear to be a Sardes SQLite database. "
                    "The application id set in the database is {}, "
                    "but should be {}.").format(
                        self._database, app_id, APPLICATION_ID))
                sqlite3.DatabaseError()
            elif version < CURRENT_SCHEMA_VERSION:
                self._connection = None
                self._connection_error = sqlite3.DatabaseError(_(
                    "The version of this database is {} and is outdated. "
                    "Please update your database to version {} and try again."
                    ).format(version, CURRENT_SCHEMA_VERSION))
            elif version > CURRENT_SCHEMA_VERSION:
                self._connection = None
                self._connection_error = sqlite3.DatabaseError(_(
                    "Your Sardes application is outdated and does not support "
                    "databases whose version is higher than {}. Please "
                    "update Sardes and try again."
                    ).format(CURRENT_SCHEMA_VERSION))
            else:
                self._connection = True
                self._connection_error = None

            conn.close()

    def close_connection(self):
        """
        Close the current connection with the database.
        """
        self._engine.dispose()
        self._connection = None

    # ---- Locations
    def _get_location(self, loc_id):
        """
        Return the sqlalchemy Location object corresponding to the
        specified location ID.
        """
        return (self._session.query(Location)
                .filter(Location.loc_id == loc_id)
                .one())

    # ---- Observation Wells
    def _get_sampling_feature(self, sampling_feature_uuid):
        """
        Return the sqlalchemy ObservationWell object corresponding to the
        specified sampling feature UUID.
        """
        return (
            self._session.query(SamplingFeature)
            .filter(SamplingFeature.sampling_feature_uuid ==
                    sampling_feature_uuid)
            .one())

    def _get_sampling_feature_uuid_from_name(self, sampling_feature_name):
        """
        Return the sampling feature UUID corresponding to the given
        sampling feature name.
        """
        return (
            self._session.query(SamplingFeature.sampling_feature_uuid)
            .filter(SamplingFeature.sampling_feature_name ==
                    sampling_feature_name)
            .one()
            .sampling_feature_uuid)

    def _refresh_sampling_feature_data_overview(
            self, sampling_feature_uuid=None, auto_commit=True):
        """
        Refresh the content of the table where the overview of the
        sampling feature monitoring data is cached.

        If a sampling_feature_uuid is provided, only the overview of that
        sampling feature is updated, else the content of the whole table
        is updated.
        """
        if sampling_feature_uuid is None:
            # We delete and update the content of the whole table.
            print("Updating sampling feature data overview...", end=' ')
            self._session.query(SamplingFeatureDataOverview).delete()

            sampling_feature_uuids = [
                item[0] for item in
                self._session.query(SamplingFeature.sampling_feature_uuid)]
            for sampling_feature_uuid in sampling_feature_uuids:
                self._refresh_sampling_feature_data_overview(
                    sampling_feature_uuid, auto_commit=False)
            self._session.commit()
            print("done")
        else:
            # We update the data overview only for the specified
            # sampling feature.
            select_query = (
                self._session.query(Observation.sampling_feature_uuid
                                    .label('sampling_feature_uuid'),
                                    func.max(TimeSeriesData.datetime)
                                    .label('last_date'),
                                    func.min(TimeSeriesData.datetime)
                                    .label('first_date'),
                                    func.avg(TimeSeriesData.value)
                                    .label('mean_water_level'))
                .filter(Observation.observation_id ==
                        TimeSeriesChannel.observation_id)
                .filter(TimeSeriesData.channel_id ==
                        TimeSeriesChannel.channel_id)
                .filter(TimeSeriesChannel.obs_property_id == 2)
                .filter(Observation.sampling_feature_uuid ==
                        sampling_feature_uuid)
                .one()
                )

            try:
                data_overview = (
                    self._session.query(SamplingFeatureDataOverview)
                    .filter(SamplingFeatureDataOverview
                            .sampling_feature_uuid ==
                            sampling_feature_uuid)
                    .one())
            except NoResultFound:
                if select_query[0] is None:
                    # This means either that this sampling feature doesn't
                    # exist or that there is no monitoring data associated with
                    # it. Therefore, there is no need to add anything to the
                    # data overview table.
                    return
                else:
                    data_overview = SamplingFeatureDataOverview(
                        sampling_feature_uuid=sampling_feature_uuid)
                    self._session.add(data_overview)

            if select_query[0] is None:
                # This means either that this sampling feature doesn't
                # exist or that there is no monitoring data associated with
                # it anymore. Therefore, we need to remove the corresponding
                # entry from the data overview table.
                self._session.delete(data_overview)
            else:
                data_overview.last_date = select_query[1]
                data_overview.first_date = select_query[2]
                data_overview.mean_water_level = select_query[3]

            if auto_commit:
                self._session.commit()

    def add_observation_wells_data(self, sampling_feature_uuid,
                                   attribute_values):
        """
        Add a new observation well to the database using the provided ID
        and attribute values.
        """
        # We need first to create a new location in table rsesq.localisation.
        new_location = Location()
        self._session.add(new_location)
        self._session.commit()

        # We then add the new observation well.
        new_obs_well = SamplingFeature(
            sampling_feature_uuid=sampling_feature_uuid,
            sampling_feature_type_id=1,
            loc_id=new_location.loc_id)
        self._session.add(new_obs_well)

        # We then create a new metadata object for the new observation well.
        new_obs_well._metadata = SamplingFeatureMetadata(
            sampling_feature_uuid=sampling_feature_uuid)
        self._session.commit()

        # We then set the attribute values provided in argument for this
        # new observation well if any.
        for attribute_name, attribute_value in attribute_values.items():
            self.set_observation_wells_data(
                sampling_feature_uuid,
                attribute_name,
                attribute_value,
                auto_commit=False)
        self._session.commit()

    def get_observation_wells_data(self):
        """
        Return a :class:`pandas.DataFrame` containing the information related
        to the observation wells that are saved in the database.
        """
        query = (
            self._session.query(SamplingFeature,
                                Location.latitude,
                                Location.longitude,
                                Location.municipality,
                                SamplingFeatureMetadata.in_recharge_zone,
                                SamplingFeatureMetadata.aquifer_type,
                                SamplingFeatureMetadata.confinement,
                                SamplingFeatureMetadata.common_name,
                                SamplingFeatureMetadata.aquifer_code,
                                SamplingFeatureMetadata.is_station_active,
                                SamplingFeatureMetadata.is_influenced)
            .filter(Location.loc_id == SamplingFeature.loc_id)
            .filter(SamplingFeatureMetadata.sampling_feature_uuid ==
                    SamplingFeature.sampling_feature_uuid)
            )
        obs_wells = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True)

        obs_wells.rename({'sampling_feature_name': 'obs_well_id'},
                         axis='columns', inplace=True)
        obs_wells.rename({'sampling_feature_notes': 'obs_well_notes'},
                         axis='columns', inplace=True)

        # Set the index to the observation well ids.
        obs_wells.set_index('sampling_feature_uuid', inplace=True, drop=True)

        # Replace nan by None.
        obs_wells = obs_wells.where(obs_wells.notnull(), None)

        return obs_wells

    def set_observation_wells_data(self, sampling_feature_uuid, attribute_name,
                                   attribute_value, auto_commit=True):
        """
        Save in the database the new attribute value for the observation well
        corresponding to the specified sampling feature UUID.
        """
        obs_well = self._get_sampling_feature(sampling_feature_uuid)
        if attribute_name in ['obs_well_id']:
            setattr(obs_well, 'sampling_feature_name', attribute_value)
        elif attribute_name in ['obs_well_notes']:
            setattr(obs_well, 'sampling_feature_notes', attribute_value)
        elif attribute_name in [
                'common_name', 'aquifer_type', 'confinement', 'aquifer_code',
                'in_recharge_zone', 'is_influenced', 'is_station_active',
                'obs_well_notes']:
            setattr(obs_well._metadata, attribute_name, attribute_value)
        elif attribute_name in ['latitude', 'longitude', 'municipality']:
            location = self._get_location(obs_well.loc_id)
            setattr(location, attribute_name, attribute_value)

        # Commit changes to the BD.
        if auto_commit:
            self._session.commit()

    def get_observation_wells_data_overview(self):
        """
        Return a :class:`pandas.DataFrame` containing an overview of
        the water level data that are available for each observation well
        of the monitoring network.
        """
        # Fetch data from the materialized view.
        query = self._session.query(SamplingFeatureDataOverview)
        data = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True)
        data.set_index('sampling_feature_uuid', inplace=True, drop=True)

        # Make sure first_date and last_date are considered as
        # datetime and strip the hour portion from it.
        data['first_date'] = pd.to_datetime(data['first_date']).dt.date
        data['last_date'] = pd.to_datetime(data['last_date']).dt.date

        # Round mean value.
        data['mean_water_level'] = data['mean_water_level'].round(decimals=3)
        return data

    # ---- Repere
    def _get_repere_data(self, repere_id):
        """
        Return the sqlalchemy Repere object corresponding to the
        given repere ID.
        """
        return (
            self._session.query(Repere)
            .filter(Repere.repere_uuid == repere_id)
            .one())

    def add_repere_data(self, repere_uuid, attribute_values):
        """
        Add a new observation well repere data to the database using the
        provided repere ID and attribute values.
        """
        # We create a new repere item.
        repere = Repere(repere_uuid=repere_uuid,
                        **attribute_values)
        self._session.add(repere)
        self._session.commit()

    def get_repere_data(self):
        """
        Return a :class:`pandas.DataFrame` containing the information related
        to observation wells repere data.
        """
        query = self._session.query(Repere)
        repere = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True)

        # Set the index to the observation well ids.
        repere.set_index('repere_uuid', inplace=True, drop=True)

        return repere

    def set_repere_data(self, repere_uuid, attribute_name, attribute_value,
                        auto_commit=True):
        """
        Save in the database the new attribute value for the observation well
        repere data corresponding to the specified ID.
        """
        repere = self._get_repere_data(repere_uuid)
        setattr(repere, attribute_name, attribute_value)
        if auto_commit:
            self._session.commit()

    # ---- Sondes Models
    def get_sonde_models_lib(self):
        """
        Return a :class:`pandas.DataFrame` containing the information related
        to sonde brands and models.
        """
        query = self._session.query(SondeModel)
        sonde_models = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True)

        # Combine the brand and model into a same field.
        sonde_models['sonde_brand_model'] = (
            sonde_models[['sonde_brand', 'sonde_model']].apply(
                lambda values: ' '.join([x or '' for x in values]).strip(),
                axis=1)
            )

        # Set the index to the observation well ids.
        sonde_models.set_index('sonde_model_id', inplace=True, drop=True)

        return sonde_models

    def set_sonde_models_lib(self, sonde_model_id, attribute_name,
                             attribute_value, auto_commit=True):
        """
        Save in the database the new attribute value for the sonde model
        corresponding to the specified id.
        """
        sonde = (self._session.query(SondeModel)
                 .filter(SondeModel.sonde_model_id == sonde_model_id)
                 .one())
        setattr(sonde, attribute_name, attribute_value)
        if auto_commit:
            self._session.commit()

    def add_sonde_models_lib(self, sonde_model_id, attribute_values):
        """
        Add a new sonde model to the database using the provided id
        and attribute values.
        """
        self._session.add(SondeModel(
            sonde_model_id=sonde_model_id,
            **attribute_values
            ))
        self._session.commit()

    # ---- Sondes Inventory
    def _get_sonde(self, sonde_uuid):
        """
        Return the sqlalchemy Sondes object corresponding to the
        specified sonde ID.
        """
        return (self._session.query(SondeFeature)
                .filter(SondeFeature.sonde_uuid == sonde_uuid)
                .one())

    def add_sondes_data(self, sonde_uuid, attribute_values):
        """
        Add a new sonde to the database using the provided sonde UUID
        and attribute values.
        """
        # Make sure pandas NaT are replaced by None for datetime fields
        # to avoid errors in sqlalchemy.
        for field in ['date_reception', 'date_withdrawal']:
            if pd.isnull(attribute_values.get(field, None)):
                attribute_values[field] = None

        self._session.add(SondeFeature(
            sonde_uuid=sonde_uuid,
            **attribute_values
            ))
        self._session.commit()

    def get_sondes_data(self):
        """
        Return a :class:`pandas.DataFrame` containing the information related
        to the sondes used to monitor groundwater properties in the wells.
        """
        query = self._session.query(SondeFeature)
        sondes = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True)

        # Make sure date_reception and date_withdrawal are considered as
        # datetime and strip the hour portion since it doesn't make sense here.
        sondes['date_reception'] = pd.to_datetime(
            sondes['date_reception']).dt.date
        sondes['date_withdrawal'] = pd.to_datetime(
            sondes['date_withdrawal']).dt.date

        # Set the index to the sonde ids.
        sondes.set_index('sonde_uuid', inplace=True, drop=True)

        return sondes

    def set_sondes_data(self, sonde_uuid, attribute_name, attribute_value,
                        auto_commit=True):
        """
        Save in the database the new attribute value for the sonde
        corresponding to the specified sonde UUID.
        """
        # Make sure pandas NaT are replaced by None for datetime fields
        # to avoid errors in sqlalchemy.
        if attribute_name in ['date_reception', 'date_withdrawal']:
            if pd.isnull(attribute_value):
                attribute_value = None

        sonde = self._get_sonde(sonde_uuid)
        setattr(sonde, attribute_name, attribute_value)
        if auto_commit:
            self._session.commit()

    # ---- Sonde installations
    def _get_sonde_installation(self, install_uuid):
        """
        Return the sqlalchemy SondeInstallation object corresponding to the
        specified sonde ID.
        """
        return (
            self._session.query(SondeInstallation)
            .filter(SondeInstallation.install_uuid == install_uuid)
            .one())

    def add_sonde_installations(self, new_install_uuid, attribute_values):
        """
        Add a new sonde installation to the database using the provided ID
        and attribute values.
        """
        # Make sure pandas NaT are replaced by None for datetime fields
        # to avoid errors in sqlalchemy.
        for field in ['start_date', 'end_date']:
            if pd.isnull(attribute_values.get(field, None)):
                attribute_values[field] = None

        # We first create new items in the tables process.
        new_process = Process(process_type='sonde installation')
        self._session.add(new_process)
        self._session.commit()

        # We then create a new sonde installation.
        sonde_installation = SondeInstallation(
            install_uuid=new_install_uuid,
            process_id=new_process.process_id
            )
        self._session.add(sonde_installation)
        self._session.commit()

        # We then set the attribute valuesfor this new sonde installation.
        for attribute_name, attribute_value in attribute_values.items():
            self.set_sonde_installations(
                new_install_uuid, attribute_name,
                attribute_value, auto_commit=True)
        self._session.commit()

    def get_sonde_installations(self):
        """
        Return a :class:`pandas.DataFrame` containing information related to
        sonde installations made in the observation wells of the monitoring
        network.
        """
        query = (
            self._session.query(SondeInstallation,
                                Process.sampling_feature_uuid)
            .filter(SondeInstallation.process_id == Process.process_id)
            )
        data = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True)

        # Set the index of the dataframe.
        data.set_index('install_uuid', inplace=True, drop=True)

        return data

    def set_sonde_installations(self, install_uuid, attribute_name,
                                attribute_value, auto_commit=True):
        """
        Save in the database the new attribute value for the sonde
        installation corresponding to the specified id.
        """
        # Make sure pandas NaT are replaced by None for datetime fields
        # to avoid errors in sqlalchemy.
        if attribute_name in ['start_date', 'end_date']:
            if pd.isnull(attribute_value):
                attribute_value = None

        sonde_installation = self._get_sonde_installation(install_uuid)
        if attribute_name == 'sampling_feature_uuid':
            process = self._get_process(sonde_installation.process_id)
            setattr(process, 'sampling_feature_uuid', attribute_value)
        else:
            setattr(sonde_installation, attribute_name, attribute_value)

        # Commit changes to the BD.
        if auto_commit:
            self._session.commit()

    # ---- Manual mesurements
    def _get_generic_num_value(self, gen_num_value_uuid):
        """
        Return the sqlalchemy GenericNumericalData object corresponding
        to the given ID.
        """
        return (
            self._session.query(GenericNumericalData)
            .filter(GenericNumericalData.gen_num_value_uuid ==
                    gen_num_value_uuid)
            .one())

    def add_manual_measurements(self, gen_num_value_uuid, attribute_values):
        """
        Add a new manual measurements to the database using the provided ID
        and attribute values.
        """
        # We need first to create a new observation in table observation.
        new_observation = Observation(
            obs_datetime=attribute_values.get('datetime', None),
            sampling_feature_uuid=attribute_values.get(
                'sampling_feature_uuid', None),
            obs_type_id=4
            )
        self._session.add(new_observation)
        self._session.commit()

        # We now create a new measurement in table 'generic_numerial_data'.
        measurement = GenericNumericalData(
            gen_num_value_uuid=gen_num_value_uuid,
            gen_num_value=attribute_values.get('value', None),
            observation_id=new_observation.observation_id,
            obs_property_id=2,
            gen_num_value_notes=attribute_values.get('notes', None)
            )
        self._session.add(measurement)
        self._session.commit()

    def get_manual_measurements(self):
        """
        Return a :class:`pandas.DataFrame` containing the water level manual
        measurements made in the observation wells for the entire monitoring
        network.
        """
        query = (
            self._session.query(
                GenericNumericalData.gen_num_value.label('value'),
                GenericNumericalData.gen_num_value_notes.label('notes'),
                GenericNumericalData.gen_num_value_uuid,
                Observation.obs_datetime.label('datetime'),
                Observation.sampling_feature_uuid)
            .filter(GenericNumericalData.obs_property_id == 2)
            .filter(GenericNumericalData.observation_id ==
                    Observation.observation_id)
            )
        measurements = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True)
        measurements.set_index('gen_num_value_uuid', inplace=True, drop=True)

        return measurements

    def set_manual_measurements(self, gen_num_value_uuid, attribute_name,
                                attribute_value):
        """
        Save in the database the new attribute value for the manual
        measurement corresponding to the specified id.
        """
        measurement = self._get_generic_num_value(gen_num_value_uuid)
        if attribute_name == 'sampling_feature_uuid':
            observation = self._get_observation(measurement.observation_id)
            observation.sampling_feature_uuid = attribute_value
        elif attribute_name == 'datetime':
            observation = self._get_observation(measurement.observation_uuid)
            observation.obs_datetime = attribute_value
        elif attribute_name == 'value':
            measurement.gen_num_value = float(attribute_value)
        elif attribute_name == 'notes':
            measurement.gen_num_value_notes = attribute_value
        self._session.commit()

    # ---- Timeseries
    def _get_timeseriesdata(self, date_time, obs_id, data_type):
        """
        Return the sqlalchemy TimeSeriesData object corresponding to a
        timeseries data of the database.
        """
        obs_property_id = self._get_observed_property_id(data_type)
        return (
            self._session.query(TimeSeriesData)
            .filter(TimeSeriesChannel.obs_property_id == obs_property_id)
            .filter(TimeSeriesChannel.observation_id == obs_id)
            .filter(TimeSeriesData.channel_id == TimeSeriesChannel.channel_id)
            .filter(TimeSeriesData.datetime == date_time)
            .one()
            )

    def _query_timeseriesdata(self, date_times, obs_id, data_type):
        """
        Return the sqlalchemy TimeSeriesData object corresponding to a
        timeseries data of the database.
        """
        obs_property_id = self._get_observed_property_id(data_type)
        return (
            self._session.query(TimeSeriesData)
            .filter(TimeSeriesChannel.obs_property_id == obs_property_id)
            .filter(TimeSeriesChannel.observation_id == obs_id)
            .filter(TimeSeriesData.channel_id == TimeSeriesChannel.channel_id)
            .filter(TimeSeriesData.datetime.in_(date_times))
            )

    def _clean_observation_if_null(self, obs_id):
        """
        Delete observation with to the given ID from the database
        if it is empty.
        """
        observation = self._get_observation(obs_id)
        if observation.obs_type_id == 7:
            count = (self._session.query(TimeSeriesData)
                     .filter(TimeSeriesChannel.observation_id == obs_id)
                     .filter(TimeSeriesData.channel_id ==
                             TimeSeriesChannel.channel_id)
                     .count())
            if count == 0:
                print("Deleting observation {} because it is now empty."
                      .format(observation.observation_id))
                # We need to delete each related timeseries channel along
                # with the observation.
                query = (self._session.query(TimeSeriesChannel)
                         .filter(TimeSeriesChannel.observation_id == obs_id))
                for tseries_channel in query:
                    self._session.delete(tseries_channel)
                self._session.delete(observation)
                self._session.commit()

    def get_timeseries_for_obs_well(self, sampling_feature_uuid, data_type):
        """
        Return a pandas dataframe containing the readings for the given
        data type and observation well.
        """
        data_type = DataType(data_type)
        obs_property_id = self._get_observed_property_id(data_type)
        query = (
            self._session.query(TimeSeriesData.value,
                                TimeSeriesData.datetime,
                                Observation.observation_id.label('obs_id'))
            .filter(TimeSeriesChannel.obs_property_id == obs_property_id)
            .filter(Observation.sampling_feature_uuid == sampling_feature_uuid)
            .filter(Observation.observation_id ==
                    TimeSeriesChannel.observation_id)
            .filter(TimeSeriesData.channel_id == TimeSeriesChannel.channel_id)
            )
        data = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True)
        data['datetime'] = pd.to_datetime(
            data['datetime'], format="%Y-%m-%d %H:%M:%S")
        data.rename(columns={'value': data_type}, inplace=True)

        # Add sonde serial number and installation depth to the dataframe.
        data['sonde_id'] = None
        data['install_depth'] = None
        for obs_id in data['obs_id'].unique():
            sonde_id = self._get_sonde_serial_no_from_obs_id(obs_id)
            data.loc[data['obs_id'] == obs_id, 'sonde_id'] = sonde_id
            install_depth = self._get_sonde_install_depth_from_obs_id(obs_id)
            data.loc[data['obs_id'] == obs_id, 'install_depth'] = install_depth

        # Check for duplicates along the time axis.
        duplicated = data.duplicated(subset='datetime')
        nbr_duplicated = np.sum(duplicated)
        if nbr_duplicated:
            observation_well = self._get_sampling_feature(
                sampling_feature_uuid)
            print(("Warning: {} duplicated {} entrie(s) were found while "
                   "fetching these data for well {}."
                   ).format(nbr_duplicated, data_type,
                            observation_well.sampling_feature_name))
        return data

    def add_timeseries_data(self, tseries_data, sampling_feature_uuid,
                            install_uuid=None):
        """
        Save in the database a set of timeseries data associated with the
        given well and sonde installation id.
        """
        # Format the dataframe.
        tseries_data = tseries_data.set_index(
            'datetime', drop=True, append=False)
        tseries_data = tseries_data.drop(
            [col for col in tseries_data.columns if col not in DataType],
            axis=1, errors='ignore').dropna(axis=1, how='all')
        tseries_data = tseries_data.dropna(axis=1, how='all')
        if tseries_data.empty:
            return

        # Create and add a new observation to the database.
        if install_uuid is not None:
            process_id = (
                self._session.query(SondeInstallation)
                .filter(SondeInstallation.install_uuid == install_uuid)
                .one().process_id)
        else:
            process_id = None

        try:
            observation_id = (
                self._session.query(func.max(
                    Observation.observation_id))
                .one())[0] + 1
        except TypeError:
            observation_id = 1

        self._session.add(Observation(
            observation_id=observation_id,
            sampling_feature_uuid=sampling_feature_uuid,
            process_id=process_id,
            obs_datetime=min(tseries_data.index),
            obs_type_id=7))

        # Create and add a new channel for each data type in the dataset.
        try:
            channel_id = (
                self._session.query(func.max(
                    TimeSeriesChannel.channel_id))
                .one())[0] + 1
        except TypeError:
            channel_id = 1

        channel_ids = []
        for column in tseries_data:
            channel_ids.append(channel_id)
            self._session.add(TimeSeriesChannel(
                channel_id=channel_id,
                obs_property_id=self._get_observed_property_id(column),
                observation_id=observation_id
                ))
            channel_id += 1

        # Set the channel ids as the column names of the dataset.
        tseries_data.columns = channel_ids
        tseries_data.columns.name = 'channel_id'

        # Format the data so that they can directly be inserted in
        # the database with pandas.
        tseries_data = (
            tseries_data
            .stack()
            .rename('value')
            .reset_index()
            .dropna(subset=['value'])
            )

        # Save the formatted timeseries data to the database.
        self._session.commit()
        tseries_data.to_sql(
            'timeseries_data', self._session.bind,
            if_exists='append', index=False, method='multi', chunksize=10000)
        self._session.commit()

        # Update the data overview for the given sampling feature.
        self._refresh_sampling_feature_data_overview(
            sampling_feature_uuid, auto_commit=False)
        self._session.commit()

    def save_timeseries_data_edits(self, tseries_edits):
        """
        Save in the database a set of edits that were made to to timeseries
        data that were already saved in the database.
        """
        for (date_time, obs_id, data_type) in tseries_edits.index:
            # Fetch the timeseries data orm object.
            try:
                tseries_data = self._get_timeseriesdata(
                    date_time, obs_id, data_type)
            except NoResultFound:
                obs_property_id = self._get_observed_property_id(data_type)
                try:
                    # We first check if a timeseries channel currently exist
                    # for the given observation and datatype.
                    tseries_channel = (
                        self._session.query(TimeSeriesChannel)
                        .filter(TimeSeriesChannel.obs_property_id ==
                                obs_property_id)
                        .filter(TimeSeriesChannel.observation_id == obs_id)
                        .one())
                except NoResultFound:
                    # This means we need to add a new timeseries channel.
                    tseries_channel = TimeSeriesChannel(
                        obs_property_id=obs_property_id,
                        observation_id=obs_id)
                    self._session.add(tseries_channel)
                    self._session.commit()

                # Then we add a new timeseries entry to the database.
                tseries_data = TimeSeriesData(
                    datetime=date_time,
                    channel_id=tseries_channel.channel_id)
                self._session.add(tseries_data)

            # Save the edited value.
            tseries_data.value = tseries_edits.loc[
                (date_time, obs_id, data_type), 'value']
        self._session.commit()

        # Update the data overview for the sampling features whose
        # corresponding data were affected by this change.
        sampling_feature_uuids = list(set([
            self._get_observation(obs_id).sampling_feature_uuid for
            obs_id in tseries_edits.index.get_level_values(1).unique()]))
        for sampling_feature_uuid in sampling_feature_uuids:
            self._refresh_sampling_feature_data_overview(
                sampling_feature_uuid, auto_commit=False)
        self._session.commit()

    def delete_timeseries_data(self, tseries_dels):
        """
        Delete data in the database for the observation IDs, datetime and
        data type specified in tseries_dels.
        """
        sampling_feature_uuids = set()
        for obs_id in tseries_dels['obs_id'].unique():
            sampling_feature_uuids.add(
                self._get_observation(obs_id).sampling_feature_uuid)

            sub_data = tseries_dels[tseries_dels['obs_id'] == obs_id]
            for data_type in sub_data['data_type'].unique():
                obs_property_id = self._get_observed_property_id(data_type)
                try:
                    channel_id = (
                        self._session.query(TimeSeriesChannel)
                        .filter(TimeSeriesChannel.obs_property_id ==
                                obs_property_id)
                        .filter(TimeSeriesChannel.observation_id == obs_id)
                        .one()
                        .channel_id
                        )
                except NoResultFound:
                    # This means there is no timeseries data saved for this
                    # type of data for this observation.
                    continue
                date_times = (
                    sub_data[sub_data['data_type'] == data_type]
                    ['datetime'].dt.to_pydatetime())
                for date_time in date_times:
                    self._session.execute(
                        TimeSeriesData.__table__.delete().where(and_(
                            TimeSeriesData.datetime == date_time,
                            TimeSeriesData.channel_id == channel_id)))
                self._session.commit()

            # We delete the observation from database if it is empty.
            self._clean_observation_if_null(obs_id)

        # Update the data overview for the sampling features whose
        # corresponding data were affected by this change.
        for sampling_feature_uuid in sampling_feature_uuids:
            self._refresh_sampling_feature_data_overview(
                sampling_feature_uuid, auto_commit=False)
        self._session.commit()

    # ---- Process
    def _get_process(self, process_id):
        """Return the process related to the given process_id."""
        return (self._session.query(Process)
                .filter(Process.process_id == process_id)
                .one())

    # ---- Observations
    def _get_observation(self, observation_id):
        """
        Return the observation related to the given id.
        """
        return (self._session.query(Observation)
                .filter(Observation.observation_id == observation_id)
                .one())

    def _get_observed_property_id(self, data_type):
        """
        Return the observed property ID for the given data type.
        """
        return {DataType.WaterLevel: 2,
                DataType.WaterTemp: 1,
                DataType.WaterEC: 3}[DataType(data_type)]

    def _get_observed_property(self, obs_property_id):
        """
        Return the sqlalchemy ObservationProperty object corresponding to the
        given ID.
        """
        return (
            self._session.query(ObservedProperty)
            .filter(ObservedProperty.obs_property_id == obs_property_id)
            .one())

    def _get_sonde_serial_no_from_obs_id(self, observation_id):
        """
        Return the sonde ID associated with the given observation ID.
        """
        try:
            return (
                self._session.query(SondeFeature)
                .filter(Observation.observation_id == observation_id)
                .filter(Observation.process_id == SondeInstallation.process_id)
                .filter(SondeInstallation.sonde_uuid ==
                        SondeFeature.sonde_uuid)
                .one()
                .sonde_serial_no)
        except NoResultFound:
            return None

    def _get_sonde_install_depth_from_obs_id(self, observation_id):
        """
        Return the installation depth of the sonde for the given
        observation ID.
        """
        try:
            return (
                self._session.query(SondeInstallation)
                .filter(Observation.observation_id == observation_id)
                .filter(Observation.process_id == SondeInstallation.process_id)
                .one()
                .install_depth)
        except NoResultFound:
            return None


# =============================================================================
# ---- Utilities
# =============================================================================
if __name__ == "__main__":
    accessor_sardeslite = DatabaseAccessorSardesLite('D:/rsesq_test.db')
    accessor_sardeslite.connect()

    # init_database(accessor_sardeslite)

    obs_wells = accessor_sardeslite.get_observation_wells_data()
    sonde_data = accessor_sardeslite.get_sondes_data()
    sonde_models_lib = accessor_sardeslite.get_sonde_models_lib()
    sonde_installations = accessor_sardeslite.get_sonde_installations()
    repere_data = accessor_sardeslite.get_repere_data()

    accessor_sardeslite.close_connection()