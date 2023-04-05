# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Sarde Lite Object-Relational Mapping and Database Accessor.
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
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.exc import DBAPIError, ProgrammingError, OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import Boolean, BLOB
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.engine.url import URL
from sqlalchemy_utils import UUIDType
from sqlalchemy.orm.exc import NoResultFound

# ---- Local imports
from sardes.config.locale import _
from sardes.api.database_accessor import (
    DatabaseAccessor, DatabaseAccessorError)
from sardes.database.accessors.accessor_errors import (
    DatabaseVersionError, SardesVersionError, DatabaseUpdateError)
from sardes.database.accessors.accessor_helpers import create_empty_readings
from sardes.database.utils import format_sqlobject_repr
from sardes.api.timeseries import DataType


# An application ID to help recognize that database files are
# specific to the current accessor.
APPLICATION_ID = 1013042054

# The latest version of the database schema.
CURRENT_SCHEMA_VERSION = 4

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

    @classmethod
    def get_primary_colnames(cls):
        mapper = inspect(cls)
        return [col for col in mapper.columns if col.primary_key]

    @classmethod
    def gen_new_ids(cls, session, n):
        """
        Generate a list of new primary key ids to use for new objects.
        """
        primary_columns = cls.get_primary_colnames()
        if len(primary_columns) == 0:
            raise ValueError('No primary key found.')
        elif len(primary_columns) > 1:
            raise ValueError('More than one primary key found.')

        primary_column = primary_columns[0]
        if isinstance(primary_column.type, UUIDType):
            return [uuid.uuid4() for i in range(n)]
        elif isinstance(primary_column.type, Integer):
            try:
                max_commited_id = (
                    session.query(func.max(getattr(cls, primary_column.name)))
                    .one()
                    )[0] + 1
            except TypeError:
                max_commited_id = 1
            return [i + max_commited_id for i in range(n)]


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

    remark_id = Column(Integer, primary_key=True)
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
    in_recharge_zone = Column(Integer)
    aquifer_type = Column(String)
    confinement = Column(String)
    common_name = Column(String)
    aquifer_code = Column(Integer)
    is_station_active = Column(Boolean)
    is_influenced = Column(Integer)

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


class MeasurementUnits(BaseMixin, Base):
    """
    An object used to map the 'measurement_units' library.
    """
    __tablename__ = 'measurement_units'

    meas_units_id = Column(Integer, primary_key=True)
    meas_units_abb = Column(String)
    meas_units_name = Column(String)
    meas_units_desc = Column(String)


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


# ---- Hydrogeochemistry
class HGLab(BaseMixin, Base):
    """
    An object used to map the 'hg_labs' library.
    """
    __tablename__ = 'hg_labs'

    lab_id = Column(Integer, primary_key=True)
    lab_code = Column(String)
    lab_name = Column(String)
    lab_contacts = Column(String)


class PumpType(BaseMixin, Base):
    """
    An object used to map the 'pump_types' library.
    """
    __tablename__ = 'pump_types'

    pump_type_id = Column(Integer, primary_key=True)
    pump_type_name = Column(String)
    pump_type_desc = Column(String)


class HGSamplingMethod(BaseMixin, Base):
    """
    An object used to map the 'hg_sampling_methods' library.
    """
    __tablename__ = 'hg_sampling_methods'

    hg_sampling_method_id = Column(Integer, primary_key=True)
    hg_sampling_method_name = Column(String)
    hg_sampling_method_desc = Column(String)


class HGParam(BaseMixin, Base):
    """
    An object used to map the 'hg_params' library.
    """
    __tablename__ = 'hg_params'

    hg_param_id = Column(Integer, primary_key=True)
    hg_param_code = Column(String)
    hg_param_name = Column(String)
    hg_param_regex = Column(String)
    cas_registry_number = Column(String)


class HGSurvey(BaseMixin, Base):
    """
    An object used to map the 'hg_surveys' library.
    """
    __tablename__ = 'hg_surveys'

    hg_survey_id = Column(Integer, primary_key=True)
    sampling_feature_uuid = Column(
        UUIDType(binary=False),
        ForeignKey('sampling_feature.sampling_feature_uuid'))
    hg_survey_datetime = Column(DateTime)
    hg_survey_depth = Column(Float)
    hg_survey_operator = Column(String)
    hg_sampling_method_id = Column(
        Integer,
        ForeignKey('hg_sampling_methods.hg_sampling_method_id'))
    sample_filtered = Column(Integer)
    survey_note = Column(String)


class HGParamValue(BaseMixin, Base):
    """
    An object used to map the 'hg_param_values' table.
    """
    __tablename__ = 'hg_param_values'

    hg_param_value_id = Column(Integer, primary_key=True)
    hg_survey_id = Column(
        Integer,
        ForeignKey('hg_surveys.hg_survey_id'))
    hg_param_id = Column(
        Integer,
        ForeignKey('hg_params.hg_param_id'))
    hg_param_value = Column(String)
    lim_detection = Column(Float)
    meas_units_id = Column(
        Integer,
        ForeignKey('measurement_units.meas_units_id'))
    lab_sample_id = Column(String)
    lab_id = Column(
        Integer,
        ForeignKey('hg_labs.lab_id'))
    lab_report_date = Column(DateTime)
    method = Column(String)
    notes = Column(String)


class Purge(BaseMixin, Base):
    """
    An object used to map the 'purge' library.
    """
    __tablename__ = 'purges'

    purge_id = Column(Integer, primary_key=True)
    hg_survey_id = Column(
        Integer,
        ForeignKey('hg_surveys.hg_survey_id'))
    purge_sequence_no = Column(Integer)
    purge_seq_start = Column(DateTime)
    purge_seq_end = Column(DateTime)
    purge_outflow = Column(Float)
    pump_type_id = Column(
        Integer,
        ForeignKey('pump_types.pump_type_id'))
    pumping_depth = Column(Float)
    water_level_drawdown = Column(Float)
    purge_notes = Column(String)


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
            # The session is already in transaction with the database, so
            # there is no need to begin a new transaction.
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
            return self._session.execute(sql_request, **kwargs)
        except ProgrammingError as p:
            print(p)
            raise p

    # ---- Database setup
    def _add_table(self, table):
        """
        Add a new table to the database.
        """
        table.__table__.create(self._session.connection())
        for item_attrs in table.initial_attrs():
            self._session.add(table(**item_attrs))
        self._session.flush()

    def _get_table_names(self):
        return inspect(self._session.connection()).get_table_names()

    def init_database(self):
        """
        Initialize the tables and attributes of a new database.
        """
        self.begin_transaction()

        existing_table_names = inspect(
            self._session.connection()
            ).get_table_names()

        tables = [Location, SamplingFeatureType, SamplingFeature,
                  SamplingFeatureMetadata, SamplingFeatureDataOverview,
                  SondeFeature, SondeModel, SondeInstallation, Process, Repere,
                  ObservationType, Observation, ObservedProperty,
                  GenericNumericalData, TimeSeriesChannel,
                  TimeSeriesData, SamplingFeatureAttachment,
                  Remark, RemarkType,
                  PumpType, HGSamplingMethod, HGParam, Purge,
                  HGSurvey, HGParamValue, MeasurementUnits, HGLab
                  ]
        for table in tables:
            if table.__tablename__ in existing_table_names:
                continue
            self._add_table(table)

        self.execute(f"PRAGMA application_id = {APPLICATION_ID}")
        self.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION}")

        self.commit_transaction()

    def update_database(self):
        """
        Update database to the latest schema version.
        """
        self.begin_transaction()
        from_version = self.version()
        self.commit_transaction()

        if from_version == CURRENT_SCHEMA_VERSION:
            return from_version, CURRENT_SCHEMA_VERSION, None

        from sardes.database.accessors.accessor_sardes_lite import (
            updates as db_updates)

        vacuum_needed = False

        to_version = 3
        if self.version() < to_version:
            self.begin_transaction()
            try:
                db_updates._update_v2_to_v3(self)
                self.execute(f"PRAGMA user_version = {to_version}")
            except Exception as error:
                self._session.rollback()
                return (from_version,
                        to_version,
                        DatabaseUpdateError(from_version, to_version, error))
            else:
                self.commit_transaction()
                vacuum_needed = True
        to_version = 4
        if self.version() < to_version:
            self.begin_transaction()
            try:
                db_updates._update_v3_to_v4(self)
                self.execute(f"PRAGMA user_version = {to_version}")
            except Exception as error:
                self._session.rollback()
                return (from_version,
                        to_version,
                        DatabaseUpdateError(from_version, to_version, error))
            else:
                self.commit_transaction()
        if vacuum_needed is True:
            # We cannot do a vacuum from within a transaction.
            # TODO: implement a new vacuum method that handle the case
            # when the database is locked.
            self._engine.execute("vacuum")
        return from_version, CURRENT_SCHEMA_VERSION, None

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
            self.begin_transaction()
        except DBAPIError as e:
            connection = None
            connection_error = e
        else:
            # We use the engine to fetch the 'application_id' and
            # 'user_version' to avoid beginning a new transaction in
            # the session.
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
            self.commit_transaction()
        return connection, connection_error

    def close_connection(self):
        """
        Close the current connection with the database.
        """
        self._session.rollback()
        self._engine.dispose()
        self._connection = None

    # ---- Measurement Units Interface
    def _get_measurement_units(self):
        return self._get_table_data(MeasurementUnits)

    def _set_measurement_units(self, index, values):
        return self._set_table_data(MeasurementUnits, index, values)

    def _add_measurement_units(self, values, indexes=None):
        return self._add_table_data(MeasurementUnits, values, indexes)

    def _del_measurement_units(self, meas_units_ids):
        return self._del_table_data(
            MeasurementUnits,
            meas_units_ids,
            foreign_constraints=[(HGParamValue, 'meas_units_id')]
            )

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
            index_col='sampling_feature_uuid',
            dtype={'aquifer_code': 'Int64',
                   'in_recharge_zone': 'Int64',
                   'is_influenced': 'Int64'}
            )

        # Replace nan by None.
        obs_wells = obs_wells.where(obs_wells.notnull(), None)

        return obs_wells

    def _add_observation_wells_data(self, values, indexes=None):
        n = len(values)

        # Generate new indexes if needed.
        if indexes is None:
            indexes = SamplingFeature.gen_new_ids(self._session, n)

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
        for table in [Observation, Process, Repere, Remark]:
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
        return self._get_table_data(
            Repere,
            parse_dates={'start_date': TO_DATETIME_ARGS,
                         'end_date': TO_DATETIME_ARGS}
            )

    def _add_repere_data(self, values, indexes=None):
        return self._add_table_data(
            Repere, values, indexes,
            datetime_fields=['start_date', 'end_date']
            )

    def _set_repere_data(self, index, values):
        return self._set_table_data(
            Repere, index, values,
            datetime_fields=['start_date', 'end_date']
            )

    def _del_repere_data(self, repere_ids):
        return self._del_table_data(Repere, repere_ids)

    # ---- Sondes Models Interface
    def _get_sonde_models_lib(self):
        sonde_models = self._get_table_data(SondeModel)

        # Combine the brand and model into a same field.
        sonde_models['sonde_brand_model'] = (
            sonde_models[['sonde_brand', 'sonde_model']].apply(
                lambda values: ' '.join([x or '' for x in values]).strip(),
                axis=1)
            )

        return sonde_models

    def _set_sonde_models_lib(self, index, values):
        return self._set_table_data(SondeModel, index, values)

    def _add_sonde_models_lib(self, values, indexes=None):
        return self._add_table_data(
            SondeModel, values, indexes,
            datetime_fields=['period_start', 'period_end', 'remark_date']
            )

    def _del_sonde_models_lib(self, sonde_model_ids):
        return self._del_table_data(
            SondeModel,
            sonde_model_ids,
            foreign_constraints=[(SondeFeature, 'sonde_model_id')]
            )

    # ---- Sondes Inventory Interface
    def _get_sondes_data(self):
        sondes_data = self._get_table_data(
            SondeFeature,
            dtype={'in_repair': 'boolean',
                   'out_of_order': 'boolean',
                   'lost': 'boolean',
                   'off_network': 'boolean'},
            parse_dates={'date_reception': TO_DATETIME_ARGS,
                         'date_withdrawal': TO_DATETIME_ARGS}
            )

        # Strip the hour portion since it doesn't make sense here.
        for column in ['date_reception', 'date_withdrawal']:
            sondes_data[column] = sondes_data[column].dt.normalize()

        return sondes_data

    def _add_sondes_data(self, values, indexes=None):
        return self._add_table_data(
            SondeFeature, values, indexes,
            datetime_fields=['date_reception', 'date_withdrawal']
            )

    def _set_sondes_data(self, index, values):
        return self._set_table_data(
            SondeFeature, index, values,
            datetime_fields=['date_reception', 'date_withdrawal']
            )

    def _del_sondes_data(self, sonde_ids):
        return self._del_table_data(
            SondeFeature, sonde_ids,
            foreign_constraints=[(SondeInstallation, 'sonde_uuid')]
            )

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
            indexes = SondeInstallation.gen_new_ids(self._session, n)

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
            indexes = GenericNumericalData.gen_new_ids(self._session, n)

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

    # ---- Remarks interface
    def _get_remarks(self):
        return self._get_table_data(
            Remark,
            dtype={'remark_type_id': 'Int64'},
            parse_dates={'period_start': TO_DATETIME_ARGS,
                         'period_end': TO_DATETIME_ARGS,
                         'remark_date': TO_DATETIME_ARGS}
            )

    def _set_remarks(self, index, values):
        return self._set_table_data(
            Remark, index, values,
            datetime_fields=('period_start', 'period_end', 'remark_date')
            )

    def _add_remarks(self, values, indexes=None):
        return self._add_table_data(
            Remark, values, indexes,
            datetime_fields=['period_start', 'period_end', 'remark_date']
            )

    def _del_remarks(self, remark_ids):
        return self._del_table_data(Remark, remark_ids)

    # ---- Remark Types interface
    def _get_remark_types(self):
        return self._get_table_data(RemarkType)

    def _set_remark_types(self, index, values):
        return self._set_table_data(RemarkType, index, values)

    def _add_remark_types(self, values, indexes=None):
        return self._add_table_data(RemarkType, values, indexes)

    def _del_remark_types(self, remark_type_ids):
        return self._del_table_data(
            RemarkType,
            remark_type_ids,
            foreign_constraints=[(Remark, 'remark_type_id')]
            )

    # ---- HG Labs interface
    def _get_hg_labs(self):
        return self._get_table_data(HGLab)

    def _set_hg_labs(self, index, values):
        return self._set_table_data(HGLab, index, values)

    def _add_hg_labs(self, values, indexes=None):
        return self._add_table_data(HGLab, values, indexes)

    def _del_hg_labs(self, indexes):
        return self._del_table_data(
            HGLab,
            indexes,
            foreign_constraints=[(HGParamValue, 'lab_id')]
            )

    # ---- Pump Types interface
    def _get_pump_types(self):
        return self._get_table_data(PumpType)

    def _set_pump_types(self, index, values):
        return self._set_table_data(PumpType, index, values)

    def _add_pump_types(self, values, indexes=None):
        return self._add_table_data(PumpType, values, indexes)

    def _del_pump_types(self, pump_type_ids):
        return self._del_table_data(
            PumpType,
            pump_type_ids,
            foreign_constraints=[(Purge, 'pump_type_id')]
            )

    # ---- HG Sampling Methods interface
    def _get_hg_sampling_methods(self):
        return self._get_table_data(HGSamplingMethod)

    def _set_hg_sampling_methods(self, index, values):
        return self._set_table_data(HGSamplingMethod, index, values)

    def _add_hg_sampling_methods(self, values, indexes=None):
        return self._add_table_data(HGSamplingMethod, values, indexes)

    def _del_hg_sampling_methods(self, indexes):
        return self._del_table_data(
            HGSamplingMethod,
            indexes,
            foreign_constraints=[(HGSurvey, 'hg_sampling_method_id')]
            )

    # ---- HG Params interface
    def _get_hg_params(self):
        return self._get_table_data(HGParam)

    def _set_hg_params(self, index, values):
        return self._set_table_data(HGParam, index, values)

    def _add_hg_params(self, values, indexes=None):
        return self._add_table_data(HGParam, values, indexes)

    def _del_hg_params(self, indexes):
        return self._del_table_data(
            HGParam,
            indexes,
            foreign_constraints=[(HGParamValue, 'hg_param_id')]
            )

    # ---- HG Surveys
    def _get_hg_surveys(self):
        return self._get_table_data(
            HGSurvey,
            dtype={'hg_sampling_method_id': 'Int64',
                   'sample_filtered': 'Int64'},
            parse_dates={'hg_survey_datetime': TO_DATETIME_ARGS,
                         'lab_report_date': TO_DATETIME_ARGS}
            )

    def _set_hg_surveys(self, index, values):
        return self._set_table_data(
            HGSurvey, index, values,
            datetime_fields=['hg_survey_datetime', 'lab_report_date']
            )

    def _add_hg_surveys(self, values, indexes=None):
        return self._add_table_data(
            HGSurvey, values, indexes,
            datetime_fields=['hg_survey_datetime', 'lab_report_date']
            )

    def _del_hg_surveys(self, indexes):
        return self._del_table_data(
            HGSurvey, indexes,
            foreign_constraints=[
                (HGParamValue, 'hg_survey_id'),
                (Purge, 'hg_survey_id')]
            )

    # ---- HG Parameter Values Interface
    def _get_hg_param_values(self):
        return self._get_table_data(
            HGParamValue,
            dtype={'hg_survey_id': 'Int64',
                   'hg_param_id': 'Int64',
                   'hg_param_value': 'object',
                   'lim_detection': 'float64',
                   'meas_units_id': 'Int64',
                   'method': 'object',
                   'lab_id': 'Int64',
                   'lab_sample_id': 'object'},
            parse_dates={'lab_report_date': TO_DATETIME_ARGS}
            )

    def _set_hg_param_values(self, index, values):
        return self._set_table_data(
            HGParamValue, index, values,
            datetime_fields=['lab_report_date']
            )

    def _add_hg_param_values(self, values, indexes=None):
        return self._add_table_data(
            HGParamValue, values, indexes,
            datetime_fields=['lab_report_date']
            )

    def _del_hg_param_values(self, indexes):
        return self._del_table_data(HGParamValue, indexes)

    # ---- Purges interface
    def _get_purges(self):
        return self._get_table_data(
            Purge,
            dtype={'hg_survey_id': 'Int64',
                   'purge_sequence_no': 'Int64',
                   'pump_type_id': 'Int64'},
            parse_dates={'purge_seq_start': TO_DATETIME_ARGS,
                         'purge_seq_end': TO_DATETIME_ARGS}
            )

    def _set_purges(self, index, values):
        return self._set_table_data(
            Purge, index, values,
            datetime_fields=['purge_seq_start', 'purge_seq_end']
            )

    def _add_purges(self, values, indexes=None):
        return self._add_table_data(
            Purge, values, indexes,
            datetime_fields=['purge_seq_start', 'purge_seq_end']
            )

    def _del_purges(self, indexes):
        return self._del_table_data(Purge, indexes)

    # ---- Generic methods
    def _get_table_primary_key(self, Table):
        primary_column = Table.get_primary_colnames()
        if len(primary_column) == 0:
            raise ValueError('No primary key found.')
        elif len(primary_column) > 1:
            raise ValueError('More than one primary key found.')
        return primary_column[0].name

    def _get_table_data(self, Table, **kwargs):
        primary_key = self._get_table_primary_key(Table)
        query = self._session.query(Table)
        data = pd.read_sql_query(
            query.statement, self._session.connection(), coerce_float=True,
            index_col=primary_key,
            **kwargs)
        return data

    def _set_table_data(self, Table, index, values, datetime_fields=()):
        primary_key = self._get_table_primary_key(Table)
        table_item = (
            self._session.query(Table)
            .filter(getattr(Table, primary_key) == index)
            .one())
        for attr_name, attr_value in values.items():
            # Make sure pandas NaT are replaced by None for datetime fields
            # to avoid errors in sqlalchemy.
            if attr_name in datetime_fields:
                attr_value = None if pd.isnull(attr_value) else attr_value

            setattr(table_item, attr_name, attr_value)

    def _add_table_data(self, Table, values, indexes=None, datetime_fields=()):
        n = len(values)

        # Generate new indexes if needed.
        if indexes is None:
            indexes = Table.gen_new_ids(self._session, n)

        # Make sure pandas NaT are replaced by None for datetime fields
        # to avoid errors in sqlalchemy.
        for i in range(n):
            for field in datetime_fields:
                if pd.isnull(values[i].get(field, True)):
                    values[i][field] = None

        primary_key = self._get_table_primary_key(Table)
        self._session.add_all([
            Table(
                **{primary_key: indexes[i]},
                **values[i]
                ) for i in range(n)
            ])
        self._session.flush()

        return indexes

    def _del_table_data(self, Table, del_indexes, foreign_constraints=()):
        # Check for foreign key violation.
        for ForeignTable, foreign_key in foreign_constraints:
            foreign_items_count = (
                self._session.query(ForeignTable)
                .filter(getattr(ForeignTable, foreign_key).in_(del_indexes))
                .count()
                )
            if foreign_items_count > 0:
                raise DatabaseAccessorError(
                    self,
                    f"Deleting {Table.__name__} items violate foreign key"
                    f"contraint on {ForeignTable.__name__}.{foreign_key}."
                    )

        # Delete the table items from the database.
        primary_key = self._get_table_primary_key(Table)
        self._session.execute(
            Table.__table__.delete().where(
                getattr(Table, primary_key).in_(del_indexes)))
        self._session.flush()

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
        return self._get_table_data(Process)

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
        return self._get_table_data(Observation)

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
    database = "D:/Desktop/rsesq_prod_28-12-2022_jsg.db"

    # import logging
    # engine_logger = logging.getLogger('sqlalchemy.engine')
    # file_handler = logging.FileHandler('D:/Desktop/sqlalchemy_v2.log')
    # engine_logger.addHandler(file_handler)
    # engine_logger.setLevel(logging.INFO)

    dbaccessor = DatabaseAccessorSardesLite(database)
    dbaccessor.update_database()

    dbaccessor.connect()

    sonde_data = dbaccessor.get('sondes_data')
    sonde_models_lib = dbaccessor.get('sonde_models_lib')
    sonde_installations = dbaccessor.get('sonde_installations')
    repere_data = dbaccessor.get('repere_data')

    attachments_info = dbaccessor.get('attachments_info')

    overview = dbaccessor.get('observation_wells_data_overview')
    t1 = perf_counter()
    sampling_feature_uuid = (
        dbaccessor._get_sampling_feature_uuid_from_name('01070001'))
    readings = dbaccessor.get_timeseries_for_obs_well(
        sampling_feature_uuid, [DataType.WaterLevel])
    print(perf_counter() - t1)

    dbaccessor.close_connection()
