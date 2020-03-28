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
import sqlite3
import uuid

# ---- Third party imports
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, extract, func
from sqlalchemy import (Column, DateTime, Float, ForeignKey, Integer, String,
                        UniqueConstraint, Index)
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import TEXT, VARCHAR, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import URL
from sqlalchemy_utils import UUIDType

# ---- Local imports
from sardes.api.database_accessor import DatabaseAccessor
from sardes.database.utils import format_sqlobject_repr
from sardes.api.timeseries import (DataType, TimeSeriesGroup, TimeSeries,
                                   merge_timeseries_groups)


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


class Location(Base):
    """
    An object used to map the 'location' table.
    """
    __tablename__ = 'location'

    loc_id = Column(Integer, primary_key=True, nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    municipality = Column(String)

    def __repr__(self):
        return format_sqlobject_repr(self)


class Repere(Base):
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
        ForeignKey('sampling_feature.sampling_feature_uuid',
                   ondelete='CASCADE'))

    def __repr__(self):
        return format_sqlobject_repr(self)


class SamplingFeature(Base):
    """
    An object used to map the 'sampling_feature' table.
    """
    __tablename__ = 'sampling_feature'

    sampling_feature_uuid = Column(
        UUIDType(binary=False), primary_key=True, nullable=False)
    sampling_feature_name = Column(String)
    sampling_feature_notes = Column(String)
    loc_id = Column(Integer, ForeignKey('location.loc_id'))
    sampling_feature_type_id = Column(
        Integer,
        ForeignKey('sampling_feature_type.sampling_feature_type_id'))

    def __repr__(self):
        return format_sqlobject_repr(self)


class SamplingFeatureType(Base):
    """
    An object used to map the 'sampling_feature_type' library.
    """
    __tablename__ = 'sampling_feature_type'

    sampling_feature_type_id = Column(
        Integer, primary_key=True, nullable=False)
    sampling_feature_type_desc = Column(String)
    sampling_feature_type_abb = Column(String)

    def __repr__(self):
        return format_sqlobject_repr(self)


# ---- Observations
class Observation(Base):
    """
    An object used to map the 'observation' table.
    """
    __tablename__ = 'observation'

    observation_id = Column(Integer, primary_key=True)
    obs_datetime = Column(DateTime)
    sampling_feature_uuid = Column(
        UUIDType(binary=False),
        ForeignKey('sampling_feature.sampling_feature_uuid'))
    process_id = Column(Integer, ForeignKey('process.process_id'))
    obs_type_id = Column(Integer, ForeignKey('observation_type.obs_type_id'))

    def __repr__(self):
        return format_sqlobject_repr(self)


class ObservationType(Base):
    """
    An object used to map the 'observation_type' library.
    """
    __tablename__ = 'observation_type'

    obs_type_id = Column(Integer, primary_key=True)
    obs_type_abb = Column(String)
    obs_type_desc = Column(String)


class ObservedProperty(Base):
    """
    An object used to map the 'observed_property' library.
    """
    __tablename__ = 'observed_property'

    obs_property_id = Column(Integer, primary_key=True)
    obs_property_name = Column('observed_property', Integer, primary_key=True)
    obs_property_desc = Column('observed_property_description', String)
    obs_property_units = Column('unit', String)

    def __repr__(self):
        return format_sqlobject_repr(self)


# ---- Numerical Data
class TimeSeriesChannel(Base):
    """
    An object used to map the 'timeseries_channel' table.
    """
    __tablename__ = 'timeseries_channel'

    channel_id = Column(Integer, primary_key=True)
    observation_id = Column(
        Integer,
        ForeignKey('observation.observation_id',
                   ondelete='CASCADE', onupdate='CASCADE'))
    obs_property_id = Column(
        Integer, ForeignKey('observed_property.obs_property_id'))

    def __repr__(self):
        return format_sqlobject_repr(self)


class TimeSeriesData(Base):
    """
    An object used to map the 'timeseries_data' table.
    """
    __tablename__ = 'timeseries_data'

    datetime = Column(DateTime, primary_key=True)
    value = Column(Float)
    channel_id = Column(
        Integer,
        ForeignKey('timeseries_channel.channel_id',
                   ondelete='CASCADE', onupdate='CASCADE'),
        index=True, primary_key=True)


class GenericNumericalData(Base):
    """
    An object used to map the 'generique'.
    """
    __tablename__ = 'generic_numerial_data'

    gen_num_value_uuid = Column(UUIDType(binary=False), primary_key=True)
    gen_num_value = Column(Float)
    observation_id = Column(
        Integer,
        ForeignKey('observation.observation_id',
                   ondelete='CASCADE',
                   onupdate='CASCADE'))
    obs_property_id = Column(
        Integer, ForeignKey('observed_property.obs_property_id'))
    gen_num_value_notes = Column(String)
    gen_init_num_value = Column(String)

    def __repr__(self):
        return format_sqlobject_repr(self)


# ---- Sondes
class SondeFeature(Base):
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


class SondeModel(Base):
    """
    An object used to map the 'sonde_model' library.
    """
    __tablename__ = 'sonde_model'

    sonde_model_id = Column(Integer, primary_key=True, nullable=False)
    sonde_brand = Column(String)
    sonde_model = Column(String)


class SondePompeInstallation(Base):
    """
    An object used to map the 'sonde_pompe_installation' table.
    """
    __tablename__ = 'sonde_pompe_installation'

    install_uuid = Column(UUIDType(binary=False), primary_key=True)
    sonde_serial_no = Column(String)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    install_depth = Column(Float)
    sampling_feature_uuid = Column(
        UUIDType(binary=False),
        ForeignKey('sampling_feature.sampling_feature_uuid'))
    operator = Column(String)


# ---- Processes
class Process(Base):
    """
    An object used to map the 'process' table.
    """
    __tablename__ = 'process'

    process_type = Column(String)
    process_id = Column(Integer, primary_key=True)


class ProcessInstallation(Base):
    """
    An object used to map the 'process_installion' table.
    """
    __tablename__ = 'process_installion'

    install_uuid = Column(
        UUIDType(binary=False),
        ForeignKey('sonde_pompe_installation.install_uuid'))
    process_id = Column(
        Integer, ForeignKey('process.process_id'), primary_key=True)


# =============================================================================
# ---- Accessor
# =============================================================================
class DatabaseAccessorSardesLite(DatabaseAccessor):
    """
    Manage the connection and requests to a RSESQ database.
    """

    def __init__(self, database):
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
            return self._connection.execute(sql_request, **kwargs)
        except ProgrammingError as p:
            print(p)
            raise p

    def _create_index(self, name):
        """
        Return a new index that can be used subsequently to add a new item
        related to name in the database.
        """
        return uuid.uuid4()

    # ---- Database connection
    def _create_engine(self):
        """Create a SQL Alchemy engine."""
        database_url = URL('sqlite', database=self._database)
        return create_engine(database_url, echo=False,
                             connect_args={'check_same_thread': False})

    def is_connected(self):
        """Return whether a connection to a database is currently active."""
        if self._connection is None:
            return False
        else:
            return not self._connection.closed

    def _connect(self):
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

    def add_observation_wells_data(self, sampling_feature_uuid,
                                   attribute_values):
        """
        Add a new observation well to the database using the provided ID
        and attribute values.
        """
        # We need first to create a new location in table rsesq.localisation.
        new_loc_id = (
            self._session.query(func.max(Location.loc_id))
            .one())[0] + 1
        location = Location(loc_id=new_loc_id)
        self._session.add(location)

        # We then add the new observation well.
        new_obs_well = SamplingFeature(
            sampling_feature_uuid=sampling_feature_uuid,
            sampling_feature_type_id=1,
            loc_id=new_loc_id
            )
        self._session.add(new_obs_well)

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
                                Location.municipality)
            .filter(Location.loc_id == SamplingFeature.loc_id)
            )
        obs_wells = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True)

        obs_wells.rename({'sampling_feature_name': 'obs_well_id'},
                         axis='columns', inplace=True)

        # Reformat notes correctly.
        keys_in_notes = ['common_name', 'aquifer_type', 'confinement',
                         'aquifer_code', 'in_recharge_zone',
                         'is_influenced', 'is_station_active',
                         'obs_well_notes']
        split_notes = obs_wells['sampling_feature_notes'].str.split(r'\|\|')
        obs_wells.drop(labels='sampling_feature_notes', axis=1, inplace=True)
        for i, key in enumerate(keys_in_notes):
            obs_wells[key] = (
                split_notes.str[i].str.split(':').str[1].str.strip())
            obs_wells[key] = obs_wells[key][obs_wells[key] != 'NULL']

        # Convert to bool.
        obs_wells['is_station_active'] = (
            obs_wells['is_station_active']
            .map({'True': True, 'False': False}))

        # Set the index to the observation well ids.
        obs_wells.set_index(
            'sampling_feature_uuid', inplace=True, drop=True)

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
        note_attrs = [
            'common_name', 'aquifer_type', 'confinement', 'aquifer_code',
            'in_recharge_zone', 'is_influenced', 'is_station_active',
            'obs_well_notes']

        if attribute_name in ['obs_well_id']:
            setattr(obs_well, attribute_name, attribute_value)
        elif attribute_name in note_attrs:
            index = note_attrs.index(attribute_name)
            labels = [
                'nom_commu', 'aquifere', 'nappe', 'code_aqui', 'zone_rechar',
                'influences', 'station_active', 'remarque'][index]
            try:
                notes = [
                    n.strip() for n in obs_well.obs_well_notes.split(r'||')]
            except AttributeError:
                notes = [''] * len(labels)
            notes[index] = '{}: {}'.format(labels[index], attribute_value)
            obs_well.sampling_feature_notes = r' || '.join(notes)
        elif attribute_name in ['latitude', 'longitude', 'municipality']:
            location = self._get_location(obs_well.loc_id)
            setattr(location, attribute_name, attribute_value)

        # Commit changes to the BD.
        if auto_commit:
            self._session.commit()

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

    # ---- Sondes Inventory
    def _get_sonde(self, sonde_uuid):
        """
        Return the sqlalchemy Sondes object corresponding to the
        specified sonde ID.
        """
        return (self._session.query(SondeFeature)
                .filter(SondeFeature.sonde_uuid == sonde_uuid)
                .one())

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
            sonde_models[['sonde_brand', 'sonde_model']]
            .apply(lambda x: ' '.join(x), axis=1))

        # Set the index to the observation well ids.
        sonde_models.set_index('sonde_model_id', inplace=True, drop=True)

        return sonde_models

    def add_sondes_data(self, sonde_uuid, attribute_values):
        """
        Add a new sonde to the database using the provided sonde UUID
        and attribute values.
        """
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

        # Strip the hour portion since it doesn't make sense here.
        sondes['date_reception'] = sondes['date_reception'].dt.date
        sondes['date_withdrawal'] = sondes['date_withdrawal'].dt.date

        # Set the index to the sonde ids.
        sondes.set_index('sonde_uuid', inplace=True, drop=True)

        return sondes

    def set_sondes_data(self, sonde_uuid, attribute_name, attribute_value,
                        auto_commit=True):
        """
        Save in the database the new attribute value for the sonde
        corresponding to the specified sonde UUID.
        """
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
            self._session.query(SondePompeInstallation)
            .filter(SondePompeInstallation.install_uuid == install_uuid)
            .one())

    def add_sonde_installations(self, new_install_uuid, attribute_values):
        """
        Add a new sonde installation to the database using the provided ID
        and attribute values.
        """
        # We first create a new sonde installation.
        sonde_installation = SondePompeInstallation(
            install_uuid=new_install_uuid)
        self._session.add(sonde_installation)

        # We then set the attribute values for this new installation.
        for name, value in attribute_values.items():
            self.set_sonde_installations(
                new_install_uuid, name, value, auto_commit=False)

        # We then need to add a new item to tables 'process_installion'
        # and 'process'.
        new_process_id = (
            self._session.query(func.max(Process.process_id))
            )[0] + 1
        self._session.add(Process(
            process_id=new_process_id,
            process_type='sonde installation'
            ))
        self._session.add(ProcessInstallation(
            install_uuid=new_install_uuid,
            process_id=new_process_id
            ))

        # Commit changes to database.
        self._session.commit()

    def get_sonde_installations(self):
        """
        Return a :class:`pandas.DataFrame` containing information related to
        sonde installations made in the observation wells of the monitoring
        network.
        """
        query = (
            self._session.query(SondePompeInstallation)
            .filter(SondePompeInstallation.install_uuid ==
                    ProcessInstallation.install_uuid)
            .filter(Process.process_id == ProcessInstallation.process_id)
            .filter(Process.process_type == 'sonde installation')
            )
        data = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True)

        # Set the index of the dataframe.
        data.set_index('install_uuid', inplace=True, drop=True)

        # Replace sonde serial number with the corresponding sonde uuid.
        sondes_data = self.get_sondes_data()
        for index in data.index:
            sonde_serial_no = data.loc[index]['sonde_serial_no']
            if sonde_serial_no is None:
                data.loc[index, 'sonde_uuid'] = None
            else:
                sondes_data_slice = sondes_data[
                    sondes_data['sonde_serial_no'] == sonde_serial_no]
                if len(sondes_data_slice) > 0:
                    data.loc[index, 'sonde_uuid'] = sondes_data_slice.index[0]
                else:
                    data.drop(labels=index, axis=0, inplace=True)
        data.drop(labels='sonde_serial_no', axis=1, inplace=True)

        return data

    def set_sonde_installations(self, install_uuid, attribute_name,
                                attribute_value, auto_commit=True):
        """
        Save in the database the new attribute value for the sonde
        installation corresponding to the specified id.
        """
        sonde_installation = self._get_sonde_installation(install_uuid)

        if attribute_name in ['sonde_uuid']:
            attribute_name = 'sonde_serial_no'
            if attribute_value is not None:
                attribute_value = (
                    self._get_sonde(attribute_value).sonde_serial_no)
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
        # We need first to create a new observation in table rsesq.observation.
        new_observation_id = (
            self._session.query(func.max(Observation.observation_id))
            )[0] + 1
        observation = Observation(
            observation_id=new_observation_id,
            obs_datetime=attribute_values.get('datetime', None),
            sampling_feature_uuid=attribute_values.get(
                'sampling_feature_uuid', None),
            obs_type_id=4
            )
        self._session.add(observation)
        self._session.commit()

        # We now create a new measurement in table 'generic_numerial_data'.
        measurement = GenericNumericalData(
            gen_num_value_uuid=gen_num_value_uuid,
            gen_num_value=attribute_values.get('value', None),
            observation_id=observation.observation_id,
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
                self._session.delete(observation)
                self._session.commit()

    def get_timeseries_for_obs_well(self, sampling_feature_uuid, data_type):
        """
        Return a :class:`TimeSeriesGroup` object containing the
        :class:`TimeSeries` objects holding the data acquired for the
        specified monitored property in the observation well corresponding
        to the specified sampling feature ID. .
        """
        data_type = DataType(data_type)

        obs_property_id = self._get_observed_property_id(data_type)
        query = (
            self._session.query(TimeSeriesData.value,
                                TimeSeriesData.datetime,
                                Observation.observation_id)
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

        # For each channel, store the data in a time series object and
        # add it to the monitored property object.
        observed_property = self._get_observed_property(obs_property_id)
        tseries_group = TimeSeriesGroup(
            data_type,
            data_type.title,
            observed_property.obs_property_units,
            yaxis_inverted=(data_type == DataType.WaterLevel)
            )
        tseries_group.sampling_feature_name = (
            self._get_sampling_feature(sampling_feature_uuid)
            .sampling_feature_name)

        # Check for duplicates along the time axis and drop the duplicated
        # entries if any.
        duplicated = data.duplicated(subset='datetime')
        nbr_duplicated = len(duplicated[duplicated])
        if nbr_duplicated:
            observation_well = self._get_sampling_feature(
                sampling_feature_uuid)
            print(("Warning: {} duplicated {} entrie(s) were found while "
                   "fetching these data for well {}."
                   ).format(nbr_duplicated, data_type,
                            observation_well.sampling_feature_name))
            tseries_group.obs_well_id = observation_well.sampling_feature_name
        tseries_group.nbr_duplicated = nbr_duplicated

        # Set the index.
        data.set_index(['datetime'], drop=True, inplace=True)

        # Split the data in channels.
        tseries_group.duplicated_data = []
        for observation_id in data['observation_id'].unique():
            channel_data = data[data['observation_id'] == observation_id]
            duplicated = channel_data.index.duplicated()
            for dtime in channel_data.index[duplicated]:
                tseries_group.duplicated_data.append(
                    [observation_well.sampling_feature_name, dtime])
                print(observation_id, dtime)
            tseries_group.add_timeseries(TimeSeries(
                pd.Series(channel_data['value'], index=channel_data.index),
                tseries_id=observation_id,
                tseries_name=data_type.title,
                tseries_units=observed_property.obs_property_units,
                tseries_color=data_type.color,
                sonde_id=self._get_sonde_id_from_obs_id(observation_id)
                ))

        return tseries_group

    def add_timeseries_data(self, tseries_data, sampling_feature_uuid,
                            install_uuid=None):
        """
        Save in the database a set of timeseries data associated with the
        given well and sonde installation id.
        """
        # We create a new observation.
        if install_uuid is not None:
            process_id = (
                self._session.query(ProcessInstallation)
                .filter(ProcessInstallation.install_uuid == install_uuid)
                .one().process_id
                )
        new_observation_id = (
            self._session.query(
                func.max(Observation.observation_id))
            .one())[0] + 1
        new_observation = Observation(
            observation_id=new_observation_id,
            sampling_feature_uuid=sampling_feature_uuid,
            process_id=process_id,
            obs_datetime=min(tseries_data['datetime']),
            obs_type_id=7
            )
        self._session.add(new_observation)
        self._session.commit()

        date_times = list(pd.to_datetime(tseries_data['datetime']))
        for data_type in DataType:
            if data_type not in tseries_data.columns:
                continue
            new_tseries_channel_id = (
                self._session.query(
                    func.max(TimeSeriesChannel.channel_id))
                .one())[0] + 1
            new_tseries_channel = TimeSeriesChannel(
                channel_id=new_tseries_channel_id,
                obs_property_id=self._get_observed_property_id(data_type),
                observation_id=new_observation_id
                )
            self._session.add(new_tseries_channel)
            self._session.commit()

            values = tseries_data[data_type].values
            for date_time, value in zip(date_times, values):
                self._session.add(TimeSeriesData(
                    datetime=date_time,
                    value=value,
                    channel_id=new_tseries_channel_id))
            self._session.commit()
        self._session.commit()

    def save_timeseries_data_edits(self, tseries_edits):
        """
        Save in the database a set of edits that were made to to timeseries
        data that were already saved in the database.
        """
        for (date_time, obs_id, data_type) in tseries_edits.index:
            # Fetch the timeseries data orm object.
            tseries_data = self._get_timeseriesdata(
                date_time, obs_id, data_type)
            # Save the edited value.
            tseries_data.value = tseries_edits.loc[
                (date_time, obs_id, data_type), 'value']
        self._session.commit()

    def delete_timeseries_data(self, tseries_dels):
        """
        Delete data in the database for the observation IDs, datetime and
        data type specified in tseries_dels.
        """
        for obs_id in tseries_dels['obs_id'].unique():
            sub_data = tseries_dels[tseries_dels['obs_id'] == obs_id]
            for data_type in sub_data['data_type'].unique():
                date_times = (
                    sub_data[sub_data['data_type'] == data_type]
                    ['datetime'].dt.to_pydatetime())
                query = self._query_timeseriesdata(
                    date_times, obs_id, data_type)
                for tseries_data in query:
                    self._session.delete(tseries_data)
                self._session.commit()

            # We delete the observation from database if it is empty.
            self._clean_observation_if_null(obs_id)

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

    def _get_sonde_id_from_obs_id(self, observation_id):
        """
        Return the sonde ID associated with the given observation ID.
        """
        return (
            self._session.query(SondePompeInstallation)
            .filter(Observation.observation_id == observation_id)
            .filter(Observation.process_id ==
                    ProcessInstallation.process_id)
            .filter(ProcessInstallation.install_uuid ==
                    SondePompeInstallation.install_uuid)
            .one()
            .sonde_serial_no)


# =============================================================================
# ---- Utilities
# =============================================================================
def init_database(accessor):
    tables = [Location, SamplingFeatureType, SamplingFeature,
              SondeFeature, SondeModel, SondePompeInstallation,
              Process, ProcessInstallation, Repere, ObservationType,
              Observation, ObservedProperty, GenericNumericalData,
              TimeSeriesChannel, TimeSeriesData]
    for table in tables:
        if accessor._engine.dialect.has_table(
                accessor._connection, table.__tablename__):
            continue
        Base.metadata.create_all(accessor._engine, tables=[table.__table__])


def copydata_from_rsesq_postgresql(accessor_rsesq, accessor_sardeslite):
    print('Copying Location...', end=' ')
    for item in accessor_rsesq._session.query(acc_rsesq.Location):
        accessor_sardeslite._session.add(Location(
            loc_id=item.loc_id,
            latitude=item.latitude,
            longitude=item.longitude,
            municipality=item.loc_notes.split(':')[1].strip()
            ))
    accessor_sardeslite._session.commit()
    print('done')
    print('Copying SamplingFeatureType...', end=' ')
    for item in accessor_rsesq._session.query(acc_rsesq.SamplingFeatureTypes):
        accessor_sardeslite._session.add(SamplingFeatureType(
            sampling_feature_type_id=item.sampling_feature_type_id,
            sampling_feature_type_desc=item.sampling_feature_type_desc,
            sampling_feature_type_abb=item.sampling_feature_type_abb
            ))
    accessor_sardeslite._session.commit()
    print('done')
    print('Copying SamplingFeature...', end=' ')
    for item in accessor_rsesq._session.query(acc_rsesq.ObservationWell):
        accessor_sardeslite._session.add(SamplingFeature(
            sampling_feature_uuid=item.sampling_feature_uuid,
            sampling_feature_name=item.obs_well_id,
            sampling_feature_notes=item.obs_well_notes,
            loc_id=item.loc_id,
            sampling_feature_type_id=1
            ))
    accessor_sardeslite._session.commit()
    print('done')
    print('Copying SondeFeature...', end=' ')
    for item in accessor_rsesq._session.query(acc_rsesq.Sondes):
        accessor_sardeslite._session.add(SondeFeature(
            sonde_uuid=item.sonde_uuid,
            sonde_serial_no=item.sonde_serial_no,
            date_reception=item.date_reception,
            date_withdrawal=item.date_withdrawal,
            sonde_notes=item.sonde_notes,
            sonde_model_id=item.sonde_model_id,
            out_of_order=item.out_of_order,
            off_network=item.off_network,
            lost=item.lost,
            in_repair=item.in_repair
            ))
    accessor_sardeslite._session.commit()
    print('done')
    print('Copying SondeModel...', end=' ')
    for item in accessor_rsesq._session.query(acc_rsesq.SondeModels):
        accessor_sardeslite._session.add(SondeModel(
            sonde_model_id=item.sonde_model_id,
            sonde_brand=item.sonde_brand,
            sonde_model=item.sonde_model
            ))
    accessor_sardeslite._session.commit()
    print('done')
    print('Copying SondePompeInstallation...', end=' ')
    for item in accessor_rsesq._session.query(acc_rsesq.SondeInstallation):
        accessor_sardeslite._session.add(SondePompeInstallation(
            install_uuid=item.install_uuid,
            sonde_serial_no=item.sonde_serial_no,
            start_date=item.start_date,
            end_date=item.end_date,
            install_depth=item.install_depth,
            sampling_feature_uuid=item.sampling_feature_uuid,
            operator=item.operator
            ))
    accessor_sardeslite._session.commit()
    print('done')
    print('Copying Process...', end=' ')
    for item in accessor_rsesq._session.query(acc_rsesq.Processes):
        accessor_sardeslite._session.add(Process(
            process_type=item.process_type,
            process_id=item.process_id
            ))
    accessor_sardeslite._session.commit()
    print('done')
    print('Copying ProcessInstallation...', end=' ')
    for item in accessor_rsesq._session.query(acc_rsesq.ProcessesInstalls):
        sonde_installation = accessor_rsesq._get_sonde_installation(
            item.install_id)
        accessor_sardeslite._session.add(ProcessInstallation(
            install_uuid=sonde_installation.install_uuid,
            process_id=item.process_id
            ))
    accessor_sardeslite._session.commit()
    print('done')
    print('Copying Repere...', end=' ')
    for item in accessor_rsesq._session.query(acc_rsesq.Repere):
        accessor_sardeslite._session.add(Repere(
            repere_uuid=item.repere_uuid,
            top_casing_alt=item.top_casing_alt,
            casing_length=item.casing_length,
            start_date=item.start_date,
            end_date=item.end_date,
            is_alt_geodesic=item.is_alt_geodesic,
            repere_note=item.repere_note,
            sampling_feature_uuid=item.sampling_feature_uuid
            ))
    accessor_sardeslite._session.commit()
    print('done')
    print('Copying ObservationType...', end=' ')
    for item in accessor_rsesq._session.query(acc_rsesq.ObservationType):
        accessor_sardeslite._session.add(ObservationType(
            obs_type_id=item.obs_type_id,
            obs_type_abb=item.obs_type_abb,
            obs_type_desc=item.obs_type_desc
            ))
    accessor_sardeslite._session.commit()
    print('done')
    print('Copying ObservedProperty...', end=' ')
    for item in accessor_rsesq._session.query(acc_rsesq.ObservationProperty):
        accessor_sardeslite._session.add(ObservedProperty(
            obs_property_id=item.obs_property_id,
            obs_property_name=item.obs_property_name,
            obs_property_desc=item.obs_property_desc,
            obs_property_units=item.obs_property_units
            ))
    accessor_sardeslite._session.commit()
    print('done')
    return
    print('Copying Observation...', end=' ')
    for item in accessor_rsesq._session.query(acc_rsesq.Observation):
        try:
            process_id = (
                accessor_rsesq._session.query(acc_rsesq.Processes)
                .filter(acc_rsesq.Processes.process_uuid == item.process_uuid)
                .one()
                .process_id
                )
        except Exception:
            process_id = None
        accessor_sardeslite._session.add(Observation(
            observation_id=item.observation_id,
            obs_datetime=item.obs_datetime,
            sampling_feature_uuid=item.sampling_feature_uuid,
            process_id=process_id,
            obs_type_id=item.param_id
            ))
    accessor_sardeslite._session.commit()
    print('done')
    print('Copying GenericNumericalData...', end=' ')
    for item in accessor_rsesq._session.query(acc_rsesq.GenericNumericalValue):
        item_observation_id = accessor_rsesq._get_observation(
            item.observation_uuid).observation_id
        accessor_sardeslite._session.add(GenericNumericalData(
            gen_num_value_uuid=item.gen_num_value_uuid,
            gen_num_value=item.gen_num_value,
            observation_id=item_observation_id,
            obs_property_id=item.obs_property_id,
            gen_num_value_notes=item.gen_num_value_notes,
            gen_init_num_value=item.gen_init_num_value
            ))
    accessor_sardeslite._session.commit()
    print('done')
    print('Copying TimeSeriesChannel...', end=' ')
    for item in accessor_rsesq._session.query(acc_rsesq.TimeSeriesChannels):
        item_observation_id = accessor_rsesq._get_observation(
            item.observation_uuid).observation_id
        accessor_sardeslite._session.add(TimeSeriesChannel(
            channel_id=item.channel_id,
            observation_id=item_observation_id,
            obs_property_id=item.obs_property_id,
            ))
    accessor_sardeslite._session.commit()
    print('done')
    print('Copying TimeSeriesData...', end='')
    query = accessor_rsesq._session.query(acc_rsesq.TimeSeriesData)
    total = query.count()
    count = 0
    limit = 10000
    print('\rCopying TimeSeriesData... 0% ({}/{})'.format(count, total),
          end='')
    for item in query.yield_per(limit).enable_eagerloads(False):
        accessor_sardeslite._session.add(TimeSeriesData(
            datetime=item.datetime,
            value=item.value,
            channel_id=item.channel_id
            ))
        count += 1
        if count % limit == 0:
            print('\rCopying TimeSeriesData... {:0.1f}% ({}/{})'
                  .format(count/total * 100, count, total),
                  end='')
            accessor_sardeslite._session.commit()
    print('\rCopying TimeSeriesData... 100% ({}/{})'.format(total, total))


if __name__ == "__main__":
    from sardes.config.database import get_dbconfig
    from sardes.database.accessor_rsesq import DatabaseAccessorRSESQ
    import sardes.database.accessor_rsesq as acc_rsesq
    from time import perf_counter

    dbconfig = get_dbconfig('rsesq_postgresql')
    accessor_rsesq = DatabaseAccessorRSESQ(**dbconfig)
    accessor_rsesq.connect()

    accessor_sardeslite = DatabaseAccessorSardesLite('D:/rsesq_v4.db')
    accessor_sardeslite.connect()

    # init_database(accessor_sardeslite)
    # copydata_from_rsesq_postgresql(accessor_rsesq, accessor_sardeslite)

    obs_wells = accessor_sardeslite.get_observation_wells_data()
    sonde_data = accessor_sardeslite.get_sondes_data()
    sonde_models_lib = accessor_sardeslite.get_sonde_models_lib()
    sonde_installations = accessor_sardeslite.get_sonde_installations()
    repere_data = accessor_sardeslite.get_repere_data()

    t1 = perf_counter()
    print('Fetching timeseries... ', end='')
    sampling_feature_uuid = (
        accessor_sardeslite._get_sampling_feature_uuid_from_name('02340006'))
    wlevel_group = accessor_sardeslite.get_timeseries_for_obs_well(
        sampling_feature_uuid, 0)
    wlevel_tseries = wlevel_group.get_merged_timeseries()
    print('done in {:0.3f} seconds'.format(perf_counter() - t1))

    accessor_sardeslite.close_connection()
