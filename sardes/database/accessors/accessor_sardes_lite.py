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
from __future__ import annotations

# ---- Standard imports
import os.path as osp
import sqlite3
import uuid
from time import perf_counter, sleep

# ---- Third party imports
import numpy as np
import pandas as pd
from pandas.api.types import is_list_like, is_datetime64_ns_dtype
from sqlalchemy import create_engine, extract, func, and_, inspect
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
from sardes.config.locale import _
from sardes.api.database_accessor import (
    DatabaseAccessor, DatabaseAccessorError)
from sardes.database.accessors.accessor_errors import (
    DatabaseVersionError, SardesVersionError)
from sardes.database.accessors.accessor_helpers import create_empty_readings
from sardes.database.utils import format_sqlobject_repr
from sardes.api.timeseries import DataType

# An application ID to help recognize that database files are
# specific to the current accessor.
APPLICATION_ID = 1013042054

# The latest version of the database schema.
CURRENT_SCHEMA_VERSION = 2

# The format that is used to store datetime values in the database.
DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
TO_DATETIME_ARGS = {'format': DATE_FORMAT}

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


class Remark(BaseMixin, Base):
    """
    An object used to map the 'remarks' table, which contains all remarks
    pertaining to the monitoring data.
    """
    __tablename__ = 'remark'

    remarks_uuid = Column(UUIDType(binary=False), primary_key=True)
    sampling_feature_uuid = Column(
        UUIDType(binary=False),
        ForeignKey('sampling_feature.sampling_feature_uuid'))
    remark_type_id = Column(
        Integer,
        ForeignKey('remark_type.remark_type_id'))
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    remark_text = Column(String)
    remark_author = Column(String(250))
    remark_date = Column(DateTime)


class RemarkType(BaseMixin, Base):
    """
    An object used to map the 'remark_type' table, which is a library of the
    type of remarks that the 'remark' table can hold.
    """
    __tablename__ = 'remark_type'
    __table_args__ = {'sqlite_autoincrement': True}

    remark_type_id = Column(Integer, primary_key=True)
    remark_type_code = Column(String(250))
    remark_type_name = Column(String(250))
    remark_type_desc = Column(String)


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
    _begin_transaction_try_count = 0

    def __init__(self, database, *args, **kargs):
        super().__init__()
        self._database = database

        # create a SQL Alchemy engine.
        database_url = URL.create('sqlite', database=self._database)
        self._engine = create_engine(
            database_url,
            echo=False,
            connect_args={'check_same_thread': False})

        # create a session.
        Session = sessionmaker(bind=self._engine)
        self._session = Session()

    def begin_transaction(self, exclusive=True):
        """Begin a new transaction with the database."""
        if self._session.in_transaction():
            return

        ts = perf_counter()
        self._begin_transaction_try_count = 0
        while True:
            self._begin_transaction_try_count += 1
            try:
                self._session.execute("BEGIN EXCLUSIVE")
            except OperationalError as e:
                if "database is locked" in str(e.orig).lower():
                    print(('Failed to begin a new transaction after '
                           '{:0.1f} sec because database is locked by '
                           'another user (Try #{}).'
                           ).format(perf_counter() - ts,
                                    self._begin_transaction_try_count))
                    sleep(1)
                else:
                    raise e
            else:
                break

    def commit_transaction(self):
        self._session.commit()

    def req_version(self):
        """Return the required version of the database."""
        return CURRENT_SCHEMA_VERSION

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
    def _create_table(self, table):
        """
        Add a new table to the database.
        """
        Base.metadata.create_all(self._engine, tables=[table.__table__])
        for item_attrs in table.initial_attrs():
            self._session.add(table(**item_attrs))
        self._session.commit()

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
        for table in tables:
            if inspect(self._engine).has_table(table.__tablename__):
                continue
            self._create_table(table)
        self._session.commit()

        self.execute("PRAGMA application_id = {}".format(APPLICATION_ID))
        self.execute("PRAGMA user_version = {}".format(CURRENT_SCHEMA_VERSION))

    # ---- Database connection
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
                connection_error = DatabaseVersionError(
                    version, CURRENT_SCHEMA_VERSION)
            elif version > CURRENT_SCHEMA_VERSION:
                connection = None
                connection_error = SardesVersionError(
                    CURRENT_SCHEMA_VERSION)
            else:
                connection = True
                connection_error = None
            conn.close()
        return connection, connection_error

    def close_connection(self):
        """
        Close the current connection with the database.
        """
        self._session.rollback()
        self._engine.dispose()
        self._connection = None

    # ---- Observation Wells Interface
    def _get_observation_wells_data(self):
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
            query.statement, self._session.connection(), coerce_float=True,
            index_col='sampling_feature_uuid'
            )

        # Replace nan by None.
        obs_wells = obs_wells.where(obs_wells.notnull(), None)

        return obs_wells

    def _add_observation_wells_data(self, values, indexes=None):
        n = len(values)

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
            self._set_observation_wells_data(indexes[i], values[i])

        return indexes

    def _set_observation_wells_data(self, index, values):
        obs_well = self._get_sampling_feature(index)
        for attr_name, attr_value in values.items():
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
            query.statement, self._session.connection(), coerce_float=True
            )['loc_id'].values.tolist()
        self._session.execute(
            Location.__table__.delete().where(
                Location.loc_id.in_(loc_ids))
            )
        self._session.flush()

    # ---- Repere Data Interface
    def _get_repere_data(self):
        query = self._session.query(Repere)
        repere = pd.read_sql_query(
            query.statement, self._session.connection(), coerce_float=True,
            index_col='repere_uuid',
            parse_dates={'start_date': TO_DATETIME_ARGS,
                         'end_date': TO_DATETIME_ARGS}
            )

        return repere

    def _add_repere_data(self, values, indexes=None):
        n = len(values)

        # Generate new indexes if needed.
        if indexes is None:
            indexes = [uuid.uuid4() for i in range(n)]

        self._session.add_all([
            Repere(repere_uuid=index) for index in indexes
            ])
        self._session.flush()

        # Set the attribute values of the new repere data.
        for i in range(n):
            self._set_repere_data(indexes[i], values[i])

        return indexes

    def _set_repere_data(self, index, values):
        repere = (
            self._session.query(Repere)
            .filter(Repere.repere_uuid == index)
            .one())

        for attr_name, attr_value in values.items():
            if attr_name in ['start_date', 'end_date']:
                # We need to make sure pandas NaT are replaced by None
                # to avoid errors in sqlalchemy.
                attr_value = None if pd.isnull(attr_value) else attr_value
            setattr(repere, attr_name, attr_value)

    def _del_repere_data(self, repere_ids):
        self._session.execute(
            Repere.__table__.delete().where(
                Repere.repere_uuid.in_(repere_ids)))
        self._session.flush()

    # ---- Sondes Models Interface
    def _get_sonde_models_lib(self):
        query = self._session.query(SondeModel)
        sonde_models = pd.read_sql_query(
            query.statement, self._session.connection(), coerce_float=True,
            index_col='sonde_model_id')

        # Combine the brand and model into a same field.
        sonde_models['sonde_brand_model'] = (
            sonde_models[['sonde_brand', 'sonde_model']].apply(
                lambda values: ' '.join([x or '' for x in values]).strip(),
                axis=1)
            )

        return sonde_models

    def _set_sonde_models_lib(self, index, values):
        sonde = (self._session.query(SondeModel)
                 .filter(SondeModel.sonde_model_id == index)
                 .one())
        for attr_name, attr_value in values.items():
            setattr(sonde, attr_name, attr_value)

    def _add_sonde_models_lib(self, values, indexes=None):
        n = len(values)

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
                **values[i]
                ) for i in range(n)
            ])
        self._session.flush()

        return indexes

    def _del_sonde_models_lib(self, sonde_model_ids):
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
        self._session.flush()

    # ---- Sondes Inventory Interface
    def _get_sondes_data(self):
        query = self._session.query(SondeFeature)
        sondes = pd.read_sql_query(
            query.statement, self._session.connection(), coerce_float=True,
            index_col='sonde_uuid',
            dtype={'in_repair': 'boolean',
                   'out_of_order': 'boolean',
                   'lost': 'boolean',
                   'off_network': 'boolean'},
            parse_dates={'date_reception': TO_DATETIME_ARGS,
                         'date_withdrawal': TO_DATETIME_ARGS}
            )

        # Strip the hour portion since it doesn't make sense here.
        for column in ['date_reception', 'date_withdrawal']:
            sondes[column] = sondes[column].dt.normalize()

        return sondes

    def _add_sondes_data(self, values, indexes=None):
        n = len(values)

        # Generate new indexes if needed.
        if indexes is None:
            indexes = [uuid.uuid4() for i in range(n)]

        # Make sure pandas NaT are replaced by None for datetime fields
        # to avoid errors in sqlalchemy.
        for i in range(n):
            if pd.isnull(values[i].get('date_reception', True)):
                values[i]['date_reception'] = None
            if pd.isnull(values[i].get('date_withdrawal', True)):
                values[i]['date_withdrawal'] = None

        self._session.add_all([
            SondeFeature(
                sonde_uuid=indexes[i],
                **values[i]
                ) for i in range(n)
            ])
        self._session.flush()

        return indexes

    def _set_sondes_data(self, index, values):
        sonde = (
            self._session.query(SondeFeature)
            .filter(SondeFeature.sonde_uuid == index)
            .one())

        for attr_name, attr_value in values.items():
            # Make sure pandas NaT are replaced by None for datetime fields
            # to avoid errors in sqlalchemy.
            if attr_name in ['date_reception', 'date_withdrawal']:
                attr_value = None if pd.isnull(attr_value) else attr_value

            setattr(sonde, attr_name, attr_value)

    def _del_sondes_data(self, sonde_ids):
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
        self._session.flush()

    # ---- Sonde Installations Interface
    def _get_sonde_installations(self):
        query = (
            self._session.query(SondeInstallation,
                                Process.sampling_feature_uuid)
            .filter(SondeInstallation.process_id == Process.process_id)
            )
        data = pd.read_sql_query(
            query.statement, self._session.connection(), coerce_float=True,
            index_col='install_uuid',
            parse_dates={'start_date': TO_DATETIME_ARGS,
                         'end_date': TO_DATETIME_ARGS}
            )

        return data

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
            self._set_sonde_installations(indexes[i], values[i])

    def _set_sonde_installations(self, index, values):
        sonde_installation = (
            self._session.query(SondeInstallation)
            .filter(SondeInstallation.install_uuid == index)
            .one())

        for attr_name, attr_value in values.items():
            # Make sure pandas NaT are replaced by None for datetime fields
            # to avoid errors in sqlalchemy.
            if attr_name in ['start_date', 'end_date']:
                attr_value = None if pd.isnull(attr_value) else attr_value

            if attr_name == 'sampling_feature_uuid':
                process = self._get_process(sonde_installation.process_id)
                setattr(process, 'sampling_feature_uuid', attr_value)
            else:
                setattr(sonde_installation, attr_name, attr_value)

    def _del_sonde_installations(self, install_ids):
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
        self._session.flush()

    # ---- Manual mesurements Interface
    def _get_manual_measurements(self):
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
            query.statement, self._session.connection(), coerce_float=True,
            index_col='gen_num_value_uuid',
            parse_dates={'datetime': TO_DATETIME_ARGS}
            )

        return measurements

    def _add_manual_measurements(self, values, indexes=None):
        n = len(values)

        # Generate new indexes if needed.
        if indexes is None:
            indexes = [uuid.uuid4() for i in range(n)]

        # Add new observations in table observation.
        new_observations = [
            Observation(
                obs_datetime=values[i].get('datetime', None),
                sampling_feature_uuid=values[i].get(
                    'sampling_feature_uuid', None),
                obs_type_id=4) for i in range(n)
            ]
        self._session.add_all(new_observations)
        self._session.flush()

        # Add the new measurements in table 'generic_numerial_data'.
        self._session.add_all([
            GenericNumericalData(
                gen_num_value_uuid=indexes[i],
                gen_num_value=values[i].get('value', None),
                observation_id=new_observations[i].observation_id,
                obs_property_id=2,
                gen_num_value_notes=values[i].get('notes', None)
                ) for i in range(n)
            ])
        self._session.flush()

    def _set_manual_measurements(self, index, values):
        measurement = self._get_generic_num_value(index)
        for attr_name, attr_value in values.items():
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

    def _del_manual_measurements(self, gen_num_value_uuids):
        for gen_num_value_uuid in gen_num_value_uuids:
            measurement = self._get_generic_num_value(gen_num_value_uuid)
            observation = self._get_observation(measurement.observation_id)
            self._session.delete(observation)
            self._session.delete(measurement)
        self._session.flush()

    # ---- Timeseries  Interface
    def _get_observation_wells_data_overview(self):
        # Fetch data from the materialized view.
        query = self._session.query(SamplingFeatureDataOverview)
        data = pd.read_sql_query(
            query.statement, self._session.connection(), coerce_float=True,
            index_col='sampling_feature_uuid',
            parse_dates={'first_date': TO_DATETIME_ARGS,
                         'last_date': TO_DATETIME_ARGS}
            )

        # Normalize the hour portion from the datetime data.
        for column in ['first_date', 'last_date']:
            data[column] = data[column].dt.normalize()

        # Round mean value.
        data['mean_water_level'] = data['mean_water_level'].round(decimals=3)

        return data

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

    def _get_timeseries_for_obs_well(self, sampling_feature_uuid,
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
                query.statement, self._session.connection(), coerce_float=True,
                parse_dates={'datetime': TO_DATETIME_ARGS}
                )
            if tseries_data.empty:
                # This means that there is no timeseries data saved in the
                # database for this data type.
                continue

            # Format the data.
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

    def _add_timeseries_data(self, tseries_data, sampling_feature_uuid,
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

        new_observation = Observation(
            sampling_feature_uuid=sampling_feature_uuid,
            process_id=process_id,
            obs_datetime=min(tseries_data.index),
            obs_type_id=7)
        self._session.add(new_observation)
        self._session.flush()

        # Create and add a new channel for each data type in the dataset.
        new_channels = [
            TimeSeriesChannel(
                obs_property_id=self._get_observed_property_id(column),
                observation_id=new_observation.observation_id
                ) for column in tseries_data
            ]
        self._session.add_all(new_channels)
        self._session.flush()

        # Set the channel ids as the column names of the dataset.
        channel_ids = [channel.channel_id for channel in new_channels]
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
        columns = ['datetime', 'channel_id', 'value']
        sql_statement = (
            "INSERT INTO timeseries_data (datetime, channel_id, value) "
            "VALUES (:datetime, :channel_id, :value)")
        self._session.execute(
            sql_statement,
            params=tseries_data[columns].to_dict(orient='records'))
        self._session.flush()

        # Update the data overview for the given sampling feature.
        self._refresh_sampling_feature_data_overview(
            sampling_feature_uuid, auto_commit=False)

    def _save_timeseries_data_edits(self, tseries_edits):
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
                    self._session.flush()

                # Then we add a new timeseries entry to the database.
                tseries_data = TimeSeriesData(
                    datetime=date_time,
                    channel_id=tseries_channel.channel_id)
                self._session.add(tseries_data)

            # Save the edited value.
            tseries_data.value = tseries_edits.loc[
                (date_time, obs_id, data_type), 'value']
        self._session.flush()

        # Update the data overview for the sampling features whose
        # corresponding data were affected by this change.
        sampling_feature_uuids = list(set([
            self._get_observation(obs_id).sampling_feature_uuid for
            obs_id in tseries_edits.index.get_level_values(1).unique()]))
        for sampling_feature_uuid in sampling_feature_uuids:
            self._refresh_sampling_feature_data_overview(
                sampling_feature_uuid, auto_commit=False)

    def _delete_timeseries_data(self, tseries_dels):
        """
        Delete data in the database for the observation IDs, datetime and
        data type specified in tseries_dels.
        """
        sampling_feature_uuids = set()
        for obs_id in tseries_dels['obs_id'].unique():
            observation = self._get_observation(obs_id)
            sampling_feature_uuids.add(observation.sampling_feature_uuid)

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

                # We need to format pandas datetime64 to strings in order to
                # delete rows from the database directly with a SQL statement.
                date_times = (
                    sub_data[sub_data['data_type'] == data_type]
                    ['datetime'].dt.strftime(DATE_FORMAT))

                sql_statement = (
                    "DELETE FROM timeseries_data WHERE "
                    "timeseries_data.datetime = :datetime AND "
                    "timeseries_data.channel_id = :channel_id")
                params = [
                    {'datetime': date_time, 'channel_id': channel_id} for
                    date_time in date_times]
                self._session.execute(
                    sql_statement,
                    params=params)
            self._session.flush()

            # Delete the Observation from database if it is now empty.
            count = (self._session.query(TimeSeriesData)
                     .filter(TimeSeriesChannel.observation_id == obs_id)
                     .filter(TimeSeriesData.channel_id ==
                             TimeSeriesChannel.channel_id)
                     .count())
            if count == 0:
                print("Deleting observation {} because it is now empty."
                      .format(observation.observation_id))
                # Delete each related timeseries channel along
                # with the observation.
                query = (self._session.query(TimeSeriesChannel)
                         .filter(TimeSeriesChannel.observation_id == obs_id))
                for tseries_channel in query:
                    self._session.delete(tseries_channel)
                self._session.delete(observation)
                self._session.flush()

        # Update the data overview for the sampling features whose
        # corresponding data were affected by this change.
        for sampling_feature_uuid in sampling_feature_uuids:
            self._refresh_sampling_feature_data_overview(
                sampling_feature_uuid, auto_commit=False)

    # ---- Attachments Interface
    def _get_attachments_info(self):
        query = (
            self._session.query(
                SamplingFeatureAttachment.sampling_feature_uuid,
                SamplingFeatureAttachment.attachment_type)
            )
        result = pd.read_sql_query(
            query.statement, self._session.connection(), coerce_float=True)
        return result

    def get_attachment(self, sampling_feature_uuid, attachment_type):
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

    # ---- Private methods
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

    def _get_location(self, loc_id):
        """
        Return the sqlalchemy Location object corresponding to the
        specified location ID.
        """
        return (self._session.query(Location)
                .filter(Location.loc_id == loc_id)
                .one())

    def _get_process_data(self):
        """
        Return a pandas dataframe containing the content of
        the 'process' table.
        """
        query = self._session.query(Process)
        process = pd.read_sql_query(
            query.statement, self._session.connection(), coerce_float=True)
        process.set_index('process_id', inplace=True, drop=True)
        return process

    def _get_process(self, process_id):
        """Return the process related to the given process_id."""
        return (self._session.query(Process)
                .filter(Process.process_id == process_id)
                .one())

    def _get_observation_data(self):
        """
        Return a pandas dataframe containing the content of
        the 'observation' table.
        """
        query = self._session.query(Observation)
        observations = pd.read_sql_query(
            query.statement, self._session.connection(), coerce_float=True)
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

    obs_wells = accessor.get('observation_wells_data')
    sonde_data = accessor.get('sondes_data')
    sonde_models_lib = accessor.get('sonde_models_lib')
    sonde_installations = accessor.get('sonde_installations')
    repere_data = accessor.get('repere_data')

    attachments_info = accessor.get('attachments_info')

    overview = accessor.get('observation_wells_data_overview')
    from time import perf_counter
    t1 = perf_counter()
    sampling_feature_uuid = (
        accessor._get_sampling_feature_uuid_from_name('01070001'))
    readings = accessor.get_timeseries_for_obs_well(
        sampling_feature_uuid, [DataType.WaterLevel])
    print(perf_counter() - t1)

    accessor.close_connection()
