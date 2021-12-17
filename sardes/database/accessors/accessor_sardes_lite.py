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
from pandas.api.types import is_list_like, is_datetime64_ns_dtype
from sqlalchemy import create_engine, extract, func, and_
from sqlalchemy import (Column, DateTime, Float, ForeignKey, Integer, String,
                        UniqueConstraint, Index)
from sqlalchemy.exc import DBAPIError, ProgrammingError, OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import TEXT, VARCHAR, Boolean, BLOB
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.engine.url import URL
from sqlalchemy_utils import UUIDType
from sqlalchemy.orm.exc import NoResultFound

# ---- Local imports
from sardes.database.accessors.accessor_helpers import create_empty_readings
from sardes.config.locale import _
from sardes.api.database_accessor import (
    DatabaseAccessor, DatabaseAccessorError)
from sardes.database.utils import format_sqlobject_repr
from sardes.api.timeseries import DataType

# An application ID to help recognize that database files are
# specific to the current accessor.
APPLICATION_ID = 1013042054

# The latest version of the database schema.
CURRENT_SCHEMA_VERSION = 2

# The format that is used to store datetime values in the database.
DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"


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


# We need to create an adapter to handle nan type in pandas integer arrays.
# https://pandas.pydata.org/pandas-docs/stable/user_guide/integer_na.html
def adapt_pandas_nan(pandas_nan):
    return None


# Make sure pandas NaT are replaced by None for datetime fields
# to avoid errors in sqlalchemy.
def adapt_pandas_nat(pandas_nat):
    return None


sqlite3.register_adapter(np.int64, addapt_numpy_int64)
sqlite3.register_adapter(np.float64, addapt_numpy_float64)
sqlite3.register_adapter(type(pd.NA), adapt_pandas_nan)


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


class SamplingFeatureAttachment(BaseMixin, Base):
    """
    An object used to map the 'sampling_feature_attachment' table.
    """
    __tablename__ = 'sampling_feature_attachment'
    __table_args__ = {'sqlite_autoincrement': True}

    attachment_id = Column(Integer, primary_key=True)
    attachment_type = Column(Integer)
    attachment_data = Column(BLOB)
    attachment_fname = Column(String)
    sampling_feature_uuid = Column(
        UUIDType(binary=False),
        ForeignKey('sampling_feature.sampling_feature_uuid'))


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

    def commit(self):
        self._session.commit()

    def version(self):
        """Return the current version of the database."""
        return self.execute("PRAGMA user_version").first()[0]

    def application_id(self):
        """Return the application id of the database."""
        return self.execute("PRAGMA application_id").first()[0]

    def execute(self, sql_request, **kwargs):
        """Execute a SQL statement construct and return a ResultProxy."""
        try:
            return self._engine.execute(sql_request, **kwargs)
        except ProgrammingError as p:
            print(p)
            raise p

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
                  TimeSeriesData, SamplingFeatureAttachment]
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
            connection = None
            connection_error = IOError(_(
                "'{}' does not exist.").format(self._database))
            return connection, connection_error

        root, ext = osp.splitext(self._database)
        if ext != '.db':
            connection = None
            connection_error = IOError(_(
                "'{}' is not a valid database file.").format(self._database))
            return connection, connection_error

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
            connection = None
            connection_error = e
        else:
            app_id = self.application_id()
            version = self.version()
            if app_id != APPLICATION_ID:
                connection = None
                connection_error = sqlite3.DatabaseError(_(
                    "'{}' does not appear to be a Sardes SQLite database. "
                    "The application id set in the database is {}, "
                    "but should be {}.").format(
                        self._database, app_id, APPLICATION_ID))
            elif version < CURRENT_SCHEMA_VERSION:
                connection = None
                connection_error = sqlite3.DatabaseError(_(
                    "The version of this database is {} and is outdated. "
                    "Please update your database to version {} and try again."
                    ).format(version, CURRENT_SCHEMA_VERSION))
            elif version > CURRENT_SCHEMA_VERSION:
                connection = None
                connection_error = sqlite3.DatabaseError(_(
                    "Your Sardes application is outdated and does not support "
                    "databases whose version is higher than {}. Please "
                    "update Sardes and try again."
                    ).format(CURRENT_SCHEMA_VERSION))
            else:
                connection = True
                connection_error = None
            conn.close()
        return connection, connection_error

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
            print("Updating sampling feature data overview...")
            self._session.query(SamplingFeatureDataOverview).delete()

            sampling_feature_uuids = [
                item[0] for item in
                self._session.query(SamplingFeature.sampling_feature_uuid)]
            for sampling_feature_uuid in sampling_feature_uuids:
                self._refresh_sampling_feature_data_overview(
                    sampling_feature_uuid, auto_commit=False)
            self._session.commit()
            print("Successfuly updated sampling feature data overview.")
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

    def _add_observation_wells_data(self, attribute_values, indexes=None):
        n = len(attribute_values)

        # Generate new indexes if needed.
        if indexes is None:
            indexes = [uuid.uuid4() for i in range(n)]

        # Add a location for each new observation well to be added
        # to the database.
        new_locations = [Location() for i in range(n)]
        self._session.add_all(new_locations)
        self._session.flush()

        # Add the new observation wells to the database.
        new_obs_wells = [
            SamplingFeature(
                sampling_feature_uuid=index,
                sampling_feature_type_id=1,
                loc_id=location.loc_id,
                _metadata=SamplingFeatureMetadata(sampling_feature_uuid=index)
                ) for index, location in zip(indexes, new_locations)
            ]
        self._session.add_all(new_obs_wells)
        self._session.flush()

        # Set the attribute values of the new observation wells.
        for i in range(n):
            self.set_observation_wells_data(
                indexes[i], attribute_values[i])

        return indexes

    def get_observation_wells_data(self):
        query = (
            self._session.query(
                SamplingFeature.sampling_feature_uuid,
                SamplingFeature.sampling_feature_name.label('obs_well_id'),
                SamplingFeature.sampling_feature_notes.label('obs_well_notes'),
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
            query.statement, query.session.bind, coerce_float=True,
            index_col='sampling_feature_uuid'
            )

        # Replace nan by None.
        obs_wells = obs_wells.where(obs_wells.notnull(), None)

        return obs_wells

    def set_observation_wells_data(self, sampling_feature_uuid,
                                   attribute_values):
        obs_well = self._get_sampling_feature(sampling_feature_uuid)
        for attr_name, attr_value in attribute_values.items():
            if attr_name == 'obs_well_id':
                setattr(obs_well, 'sampling_feature_name', attr_value)
            elif attr_name == 'obs_well_notes':
                setattr(obs_well, 'sampling_feature_notes', attr_value)
            elif attr_name in ['common_name', 'aquifer_type', 'confinement',
                               'aquifer_code', 'in_recharge_zone',
                               'is_influenced', 'is_station_active',
                               'obs_well_notes']:
                setattr(obs_well._metadata, attr_name, attr_value)
            elif attr_name in ['latitude', 'longitude', 'municipality']:
                location = self._get_location(obs_well.loc_id)
                setattr(location, attr_name, attr_value)

    def _del_observation_wells_data(self, obswell_ids):
        # Check for foreign key violation.
        for table in [Observation, Process, Repere]:
            foreign_items_count = (
                self._session.query(table)
                .filter(table.sampling_feature_uuid.in_(obswell_ids))
                .count()
                )
            if foreign_items_count > 0:
                raise DatabaseAccessorError(
                    self,
                    "deleting SamplingFeature items violate foreign "
                    "key contraint on {}.sampling_feature_uuid."
                    .format(table.__name__))

        # Delete the SamplingFeature items from the database.
        for table in [SamplingFeature, SamplingFeatureMetadata,
                      SamplingFeatureDataOverview, SamplingFeatureAttachment]:
            self._session.execute(
                table.__table__.delete().where(
                    table.sampling_feature_uuid.in_(obswell_ids))
                )

        # Delete associated Location items from the database.
        query = (
            self._session.query(Location.loc_id)
            .filter(SamplingFeature.loc_id == Location.loc_id)
            .filter(SamplingFeature.sampling_feature_uuid.in_(obswell_ids))
            )
        loc_ids = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True
            )['loc_id'].values.tolist()
        self._session.execute(
            Location.__table__.delete().where(
                Location.loc_id.in_(loc_ids))
            )

    def get_observation_wells_data_overview(self):
        """
        Return a :class:`pandas.DataFrame` containing an overview of
        the water level data that are available for each observation well
        of the monitoring network.
        """
        # Fetch data from the materialized view.
        query = self._session.query(SamplingFeatureDataOverview)
        data = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True,
            index_col='sampling_feature_uuid')

        # TODO: when using pandas > 1.3.0, it is possible to set the dtype
        # directly in 'read_sql_query' with the new 'dtype' argument.

        # Make sure first_date and last_date are considered as
        # datetime and strip the hour portion from it.
        data['first_date'] = pd.to_datetime(data['first_date']).dt.date
        data['last_date'] = pd.to_datetime(data['last_date']).dt.date

        # Round mean value.
        data['mean_water_level'] = data['mean_water_level'].round(decimals=3)
        return data

    # ---- Attachments
    def get_stored_attachments_info(self):
        """
        Return a pandas dataframe containing a list of sampling_feature_uuid
        and attachment_type for which a file is attached in the database.
        """
        query = (
            self._session.query(
                SamplingFeatureAttachment.sampling_feature_uuid,
                SamplingFeatureAttachment.attachment_type)
            )
        result = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True)
        return result

    def get_attachment(self, sampling_feature_uuid, attachment_type):
        """
        Return the data of the file of the specified type that is
        attached to the specified station.
        """
        try:
            attachment = (
                self._session.query(SamplingFeatureAttachment)
                .filter(SamplingFeatureAttachment.sampling_feature_uuid ==
                        sampling_feature_uuid)
                .filter(SamplingFeatureAttachment.attachment_type ==
                        attachment_type)
                .one())
        except NoResultFound:
            return (None, None)
        else:
            return (attachment.attachment_data, attachment.attachment_fname)

    def set_attachment(self, sampling_feature_uuid, attachment_type,
                       filename):
        """
        Attach the data of a file to the specified sampling_feature_uuid.
        """
        try:
            # We first check if a file of this type is already attached to
            # the monitoring station.
            attachment = (
                self._session.query(SamplingFeatureAttachment)
                .filter(SamplingFeatureAttachment.sampling_feature_uuid ==
                        sampling_feature_uuid)
                .filter(SamplingFeatureAttachment.attachment_type ==
                        attachment_type)
                .one())
        except NoResultFound:
            # This means we need to add a new attachment to save the file.
            attachment = SamplingFeatureAttachment(
                attachment_type=attachment_type,
                sampling_feature_uuid=sampling_feature_uuid)
            self._session.add(attachment)

        if osp.exists(filename):
            with open(filename, 'rb') as f:
                attachment.attachment_data = memoryview(f.read())
        attachment.attachment_fname = osp.basename(filename)
        self._session.commit()

    def del_attachment(self, sampling_feature_uuid, attachment_type):
        """
        Delete the data of the file of the specified type that is attached
        to the specified sampling_feature_uuid.
        """
        try:
            attachment = (
                self._session.query(SamplingFeatureAttachment)
                .filter(SamplingFeatureAttachment.sampling_feature_uuid ==
                        sampling_feature_uuid)
                .filter(SamplingFeatureAttachment.attachment_type ==
                        attachment_type)
                .one())
        except NoResultFound:
            # This means there is currently no file of this type attached to
            # the specified sampling_feature_uuid.
            pass
        else:
            self._session.delete(attachment)
            self._session.commit()

    # ---- Repere
    def _get_repere_data(self, repere_id):
        return (
            self._session.query(Repere)
            .filter(Repere.repere_uuid == repere_id)
            .one())

    def _add_repere_data(self, attribute_values, indexes=None):
        n = len(attribute_values)

        # Generate new indexes if needed.
        if indexes is None:
            indexes = [uuid.uuid4() for i in range(n)]

        self._session.add_all([
            Repere(repere_uuid=index) for index in indexes
            ])
        self._session.flush()

        # Set the attribute values of the new repere data.
        for i in range(n):
            self.set_repere_data(
                indexes[i], attribute_values[i], auto_commit=False)

        return indexes

    def get_repere_data(self):
        """
        Return a :class:`pandas.DataFrame` containing the information related
        to observation wells repere data.
        """
        query = self._session.query(Repere)
        repere = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True,
            index_col='repere_uuid')

        # TODO: when using pandas > 1.3.0, it is possible to set the dtype
        # directly in 'read_sql_query' with the new 'dtype' argument.

        # Make sure datetime data is considered as datetime.
        # See cgq-qgc/sardes#427.
        for column in ['start_date', 'end_date']:
            if not is_datetime64_ns_dtype(repere[column]):
                print('Converting {} data to datetime.'.format(column))
                repere[column] = pd.to_datetime(repere[column])

        return repere

    def set_repere_data(self, repere_id, attribute_values, auto_commit=True):
        """
        Save in the database the new attribute values for the repere data
        corresponding to the specified repere_id.
        """
        repere = self._get_repere_data(repere_id)
        for attr_name, attr_value in attribute_values.items():
            if attr_name in ['start_date', 'end_date']:
                # We need to make sure pandas NaT are replaced by None
                # to avoid errors in sqlalchemy.
                attr_value = None if pd.isnull(attr_value) else attr_value
            setattr(repere, attr_name, attr_value)
        if auto_commit:
            self._session.commit()

    def _del_repere_data(self, repere_ids):
        self._session.execute(
            Repere.__table__.delete().where(
                Repere.repere_uuid.in_(repere_ids)))
        self._session.commit()

    # ---- Sondes Models
    def get_sonde_models_lib(self):
        """
        Return a :class:`pandas.DataFrame` containing the information related
        to sonde brands and models.
        """
        query = self._session.query(SondeModel)
        sonde_models = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True,
            index_col='sonde_model_id')

        # Combine the brand and model into a same field.
        sonde_models['sonde_brand_model'] = (
            sonde_models[['sonde_brand', 'sonde_model']].apply(
                lambda values: ' '.join([x or '' for x in values]).strip(),
                axis=1)
            )

        return sonde_models

    def set_sonde_models_lib(self, sonde_model_id, attribute_values,
                             auto_commit=True):
        """
        Save in the database the new attribute value for the sonde model
        corresponding to the specified sonde_model_id.
        """
        sonde = (self._session.query(SondeModel)
                 .filter(SondeModel.sonde_model_id == sonde_model_id)
                 .one())
        for attr_name, attr_value in attribute_values.items():
            setattr(sonde, attr_name, attr_value)
        if auto_commit:
            self._session.commit()

    def _add_sonde_models_lib(self, attribute_values, indexes=None):
        n = len(attribute_values)

        # Generate new indexes if needed.
        if indexes is None:
            try:
                max_commited_id = (
                    self._session.query(func.max(SondeModel.sonde_model_id))
                    .one())[0]
            except TypeError:
                max_commited_id = 0
            indexes = [i + max_commited_id + 1 for i in range(n)]

        self._session.add_all([
            SondeModel(
                sonde_model_id=indexes[i],
                **attribute_values[i]
                ) for i in range(n)
            ])
        self._session.flush()

        return indexes

    def _del_sonde_models_lib(self, sonde_model_ids):
        """
        Delete the sonde model corresponding to the specified sonde_model_ids.

        Note:
            This method should not be called directly. Please use instead the
            public method `delete` provided by `DatabaseAccessorBase`.
        """
        # Check for foreign key violation.
        foreign_sonde_features_count = (
            self._session.query(SondeFeature)
            .filter(SondeFeature.sonde_model_id.in_(sonde_model_ids))
            .count()
            )
        if foreign_sonde_features_count > 0:
            raise DatabaseAccessorError(
                self,
                "deleting SondeModel items violate foreign key "
                "contraint on SondeFeature.sonde_model_id."
                )

        # Delete the SondeModel items from the database.
        self._session.execute(
            SondeModel.__table__.delete().where(
                SondeModel.sonde_model_id.in_(sonde_model_ids)))
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

    def _add_sondes_data(self, attribute_values, indexes=None):
        n = len(attribute_values)

        # Generate new indexes if needed.
        if indexes is None:
            indexes = [uuid.uuid4() for i in range(n)]

        # Make sure pandas NaT are replaced by None for datetime fields
        # to avoid errors in sqlalchemy.
        for i in range(n):
            if pd.isnull(attribute_values[i].get('date_reception', True)):
                attribute_values[i]['date_reception'] = None
            if pd.isnull(attribute_values[i].get('date_withdrawal', True)):
                attribute_values[i]['date_withdrawal'] = None

        self._session.add_all([
            SondeFeature(
                sonde_uuid=indexes[i],
                **attribute_values[i]
                ) for i in range(n)
            ])
        self._session.flush()

        return indexes

    def get_sondes_data(self):
        """
        Return a :class:`pandas.DataFrame` containing the information related
        to the sondes used to monitor groundwater properties in the wells.
        """
        query = self._session.query(SondeFeature)
        sondes = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True,
            index_col='sonde_uuid')

        # TODO: when using pandas > 1.3.0, it is possible to set the dtype
        # directly in 'read_sql_query' with the new 'dtype' argument.

        # Make sure date_reception and date_withdrawal are considered as
        # datetime and strip the hour portion since it doesn't make sense here.
        sondes['date_reception'] = pd.to_datetime(
            sondes['date_reception']).dt.date
        sondes['date_withdrawal'] = pd.to_datetime(
            sondes['date_withdrawal']).dt.date

        for column in ['in_repair', 'out_of_order', 'lost', 'off_network']:
            sondes[column] = sondes[column].astype('boolean')

        return sondes

    def set_sondes_data(self, sonde_uuid, attribute_values, auto_commit=True):
        """
        Save in the database the new attribute value for the sonde
        corresponding to the specified sonde_id.
        """
        sonde = self._get_sonde(sonde_uuid)
        for attr_name, attr_value in attribute_values.items():
            # Make sure pandas NaT are replaced by None for datetime fields
            # to avoid errors in sqlalchemy.
            if attr_name in ['date_reception', 'date_withdrawal']:
                attr_value = None if pd.isnull(attr_value) else attr_value

            setattr(sonde, attr_name, attr_value)
        if auto_commit:
            self._session.commit()

    def _del_sondes_data(self, sonde_ids):
        """
        Delete the sonde data corresponding to the specified ids.

        Note:
            This method should not be called directly. Please use instead the
            public method `delete` provided by `DatabaseAccessorBase`.
        """
        # Check for foreign key violation.
        foreign_sonde_installation = (
            self._session.query(SondeInstallation)
            .filter(SondeInstallation.sonde_uuid.in_(sonde_ids))
            )
        if foreign_sonde_installation.count() > 0:
            raise DatabaseAccessorError(
                self,
                "deleting SondeFeature items violate foreign key "
                "constraint on SondeInstallation.sonde_uuid."
                )

        # Delete the SondeFeature items from the database.
        self._session.execute(
            SondeFeature.__table__.delete().where(
                SondeFeature.sonde_uuid.in_(sonde_ids)))
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

    def _add_sonde_installations(self, values, indexes=None):
        n = len(values)

        # Generate new indexes if needed.
        if indexes is None:
            indexes = [uuid.uuid4() for i in range(n)]

        # Make sure pandas NaT are replaced by None for datetime fields
        # to avoid errors in sqlalchemy.
        for i in range(n):
            if pd.isnull(values[i].get('start_date', True)):
                values[i]['start_date'] = None
            if pd.isnull(values[i].get('end_date', True)):
                values[i]['end_date'] = None

        # Add new items to the tables process.
        new_processes = [
            Process(process_type='sonde installation') for i in range(n)]
        self._session.add_all(new_processes)
        self._session.flush()

        # Add the new sonde installations.
        self._session.add_all([
            SondeInstallation(
                install_uuid=indexes[i],
                process_id=new_processes[i].process_id
                ) for i in range(n)
            ])
        self._session.flush()

        # We then set the attribute valuesfor this new sonde installation.
        for i in range(n):
            self.set_sonde_installations(
                indexes[i], values[i], auto_commit=False)

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
            query.statement, query.session.bind, coerce_float=True,
            index_col='install_uuid')

        # TODO: when using pandas > 1.3.0, it is possible to set the dtype
        # directly in 'read_sql_query' with the new 'dtype' argument.

        # Format the data.
        data['start_date'] = pd.to_datetime(data['start_date'])
        data['end_date'] = pd.to_datetime(data['end_date'])

        return data

    def set_sonde_installations(self, install_uuid, attribute_values,
                                auto_commit=True):
        """
        Save in the database the new attribute values for the sonde
        installation corresponding to the specified installation_id.
        """
        sonde_installation = self._get_sonde_installation(install_uuid)
        for attr_name, attr_value in attribute_values.items():
            # Make sure pandas NaT are replaced by None for datetime fields
            # to avoid errors in sqlalchemy.
            if attr_name in ['start_date', 'end_date']:
                attr_value = None if pd.isnull(attr_value) else attr_value

            if attr_name == 'sampling_feature_uuid':
                process = self._get_process(sonde_installation.process_id)
                setattr(process, 'sampling_feature_uuid', attr_value)
            else:
                setattr(sonde_installation, attr_name, attr_value)

        # Commit changes to the BD.
        if auto_commit:
            self._session.commit()

    def _del_sonde_installations(self, install_ids):
        """
        Delete the sonde installations corresponding to the specified ids.

        Note:
            This method should not be called directly. Please use instead the
            public method `delete` provided by `DatabaseAccessorBase`.
        """
        # We need to update the "observations" and "process" tables to remove
        # any reference to the sonde installations that are going to be
        # removed from the database.
        observations = (
            self._session.query(Observation)
            .filter(SondeInstallation.install_uuid.in_(install_ids))
            .filter(Observation.process_id == SondeInstallation.process_id)
            )
        for observation in observations:
            observation.process_id = None

        processes = (
            self._session.query(Process)
            .filter(SondeInstallation.install_uuid.in_(install_ids))
            .filter(Process.process_id == SondeInstallation.process_id)
            )
        for process in processes:
            self._session.delete(process)

        # Delete the SondeInstallation items from the database.
        self._session.execute(
            SondeInstallation.__table__.delete().where(
                SondeInstallation.install_uuid.in_(install_ids)))
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
            query.statement, query.session.bind, coerce_float=True,
            index_col='gen_num_value_uuid')

        # TODO: when using pandas > 1.3.0, it is possible to set the dtype
        # directly in 'read_sql_query' with the new 'dtype' argument.

        # Make sure datetime data is considered as datetime.
        # This is required to avoid problems when the manual measurements
        # table is empty. See cgq-qgc/sardes#427.
        if not is_datetime64_ns_dtype(measurements['datetime']):
            print('Converting manual measurements to datetime.')
            measurements['datetime'] = pd.to_datetime(measurements['datetime'])

        return measurements

    def set_manual_measurements(self, gen_num_value_uuid, attribute_values):
        """
        Save in the database the new attribute value for the manual
        measurement corresponding to the specified id.
        """
        measurement = self._get_generic_num_value(gen_num_value_uuid)
        for attr_name, attr_value in attribute_values.items():
            if attr_name == 'sampling_feature_uuid':
                observation = self._get_observation(measurement.observation_id)
                observation.sampling_feature_uuid = attr_value
            elif attr_name == 'datetime':
                # We need to make sure pandas NaT are replaced by None
                # to avoid errors in sqlalchemy.
                attr_value = None if pd.isnull(attr_value) else attr_value

                observation = self._get_observation(measurement.observation_id)
                observation.obs_datetime = attr_value
            elif attr_name == 'value':
                measurement.gen_num_value = float(attr_value)
            elif attr_name == 'notes':
                measurement.gen_num_value_notes = attr_value
        self._session.commit()

    def _del_manual_measurements(self, gen_num_value_uuids):
        """
        Delete the manual measurements corresponding to the specified
        gen_num_value_uuids.

        Note:
            This method should not be called directly. Please use instead the
            public method `delete` provided by `DatabaseAccessorBase`.
        """
        for gen_num_value_uuid in gen_num_value_uuids:
            measurement = self._get_generic_num_value(gen_num_value_uuid)
            observation = self._get_observation(measurement.observation_id)
            self._session.delete(observation)
            self._session.delete(measurement)
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

    def get_timeseries_for_obs_well(self, sampling_feature_uuid,
                                    data_types=None):
        """
        Return a pandas dataframe containing the readings for the given
        data types and monitoring station.

        If no data type are specified, then return the entire dataset for
        the specified monitoring station.
        """
        if isinstance(data_types, str) or isinstance(data_types, DataType):
            data_types = [data_types, ]
        if data_types is None:
            data_types = [
                DataType.WaterLevel,
                DataType.WaterTemp,
                DataType.WaterEC]
        else:
            data_types = [
                DataType[data_type] if isinstance(data_type, str) else
                DataType(data_type) for data_type in data_types]

        readings_data = None
        added_data_types = []
        for data_type in data_types:
            obs_property_id = self._get_observed_property_id(data_type)
            query = (
                self._session.query(TimeSeriesData.value,
                                    TimeSeriesData.datetime,
                                    Observation.observation_id.label('obs_id'))
                .filter(TimeSeriesChannel.obs_property_id == obs_property_id)
                .filter(Observation.sampling_feature_uuid ==
                        sampling_feature_uuid)
                .filter(Observation.observation_id ==
                        TimeSeriesChannel.observation_id)
                .filter(TimeSeriesData.channel_id ==
                        TimeSeriesChannel.channel_id)
                )
            tseries_data = pd.read_sql_query(
                query.statement, query.session.bind, coerce_float=True)
            if tseries_data.empty:
                # This means that there is no timeseries data saved in the
                # database for this data type.
                continue

            # Format the data.
            if not is_datetime64_ns_dtype(tseries_data['datetime']):
                tseries_data['datetime'] = pd.to_datetime(
                    tseries_data['datetime'], format=DATE_FORMAT)
            tseries_data.rename(columns={'value': data_type}, inplace=True)

            # Merge the data.
            added_data_types.append(data_type)
            if readings_data is None:
                readings_data = tseries_data
            else:
                readings_data = readings_data.merge(
                    tseries_data,
                    left_on=['datetime', 'obs_id'],
                    right_on=['datetime', 'obs_id'],
                    how='outer', sort=True)
        if readings_data is None:
            # This means there is no reading saved for this monitoring
            # station in the database.
            return create_empty_readings(data_types)

        # Add sonde serial number and installation depth to the dataframe.
        readings_data['sonde_id'] = None
        readings_data['install_depth'] = None
        for obs_id in readings_data['obs_id'].unique():
            sonde_id = self._get_sonde_serial_no_from_obs_id(obs_id)
            readings_data.loc[
                readings_data['obs_id'] == obs_id, 'sonde_id'
                ] = sonde_id

            install_depth = self._get_sonde_install_depth_from_obs_id(obs_id)
            readings_data.loc[
                readings_data['obs_id'] == obs_id, 'install_depth'
                ] = install_depth

        # Reorder the columns so that the data are displayed nicely and
        # sort the data by datetime.
        readings_data = readings_data[
            ['datetime', 'sonde_id'] +
            added_data_types +
            ['install_depth', 'obs_id']]
        readings_data = readings_data.sort_values(
            'datetime', axis=0, ascending=True)

        return readings_data

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
            [col for col in tseries_data.columns if
             not isinstance(col, DataType)],
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
        self._session.commit()

        # Set the channel ids as the column names of the dataset.
        tseries_data.columns = channel_ids
        tseries_data.columns.name = 'channel_id'

        # Format the data so that they can be inserted easily in
        # the database with sqlite3.
        tseries_data = (
            tseries_data
            .stack()
            .rename('value')
            .reset_index()
            .dropna(subset=['value'])
            )

        # We need to format pandas datetime64 to strings in order to save
        # them in the database with sqlite3 directly (without sqlalchemy).
        tseries_data['datetime'] = (
            tseries_data['datetime'].dt.strftime(DATE_FORMAT))

        # Save the formatted timeseries data to the database.
        conn = sqlite3.connect(self._database)
        cur = conn.cursor()
        columns = ['datetime', 'channel_id', 'value']
        sql_statement = (
            "INSERT INTO timeseries_data ({}) VALUES (?, ?, ?)"
            ).format(', '.join(columns))
        for row in tseries_data[columns].itertuples(index=False, name=None):
            cur.execute(sql_statement, row)
        conn.commit()
        conn.close()

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
                # TODO: improve by deleting chunks of data at a time.
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
    def _get_process_data(self):
        """
        Return a pandas dataframe containing the content of
        the 'process' table.
        """
        query = self._session.query(Process)
        process = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True)
        process.set_index('process_id', inplace=True, drop=True)
        return process

    def _get_process(self, process_id):
        """Return the process related to the given process_id."""
        return (self._session.query(Process)
                .filter(Process.process_id == process_id)
                .one())

    # ---- Observations
    def _get_observation_data(self):
        """
        Return a pandas dataframe containing the content of
        the 'observation' table.
        """
        query = self._session.query(Observation)
        observations = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True)
        observations.set_index('observation_id', inplace=True, drop=True)
        return observations

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


if __name__ == "__main__":
    database = "D:/Desktop/rsesq_prod_02-02-2021.db"
    accessor = DatabaseAccessorSardesLite(database)
    accessor.init_database()
    accessor.connect()

    obs_wells = accessor.get_observation_wells_data()
    sonde_data = accessor.get_sondes_data()
    sonde_models_lib = accessor.get_sonde_models_lib()
    sonde_installations = accessor.get_sonde_installations()
    repere_data = accessor.get_repere_data()

    stored_attachments_info = accessor.get_stored_attachments_info()

    overview = accessor.get_observation_wells_data_overview()
    from time import perf_counter
    t1 = perf_counter()
    sampling_feature_uuid = (
        accessor._get_sampling_feature_uuid_from_name('01070001'))
    readings = accessor.get_timeseries_for_obs_well(
        sampling_feature_uuid, [DataType.WaterLevel])
    print(perf_counter() - t1)

    accessor.close_connection()
