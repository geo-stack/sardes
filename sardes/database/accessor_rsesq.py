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

# ---- Standard imports
import uuid

# ---- Third party imports
from geoalchemy2 import Geometry
from geoalchemy2.elements import WKTElement
import numpy as np
import pandas as pd
from psycopg2.extensions import register_adapter, AsIs
from sqlalchemy import create_engine, extract, func
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.types import TEXT, VARCHAR, Boolean

# ---- Local imports
from sardes.api.database_accessor import DatabaseAccessor
from sardes.database.utils import map_table_column_names, format_sqlobject_repr
from sardes.api.timeseries import TimeSeriesGroup, TimeSeries


# =============================================================================
# ---- Register Adapters
# =============================================================================
# This is required to avoid a "can't adapt type 'numpy.int64' or
# 'numpy.float64'" psycopg2.ProgrammingError.
# See https://stackoverflow.com/questions/50626058

def addapt_numpy_float64(numpy_float64):
    return AsIs(numpy_float64)


def addapt_numpy_int64(numpy_int64):
    return AsIs(numpy_int64)


register_adapter(np.float64, addapt_numpy_float64)
register_adapter(np.int64, addapt_numpy_int64)


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

    loc_common_name = Column('nom_communn', String)
    latitude = Column('latitude_8', Float)
    longitude = Column(Float)
    is_station_active = Column('station_active', Boolean)
    loc_notes = Column('remarque', String)
    loc_id = Column(String, primary_key=True)
    loc_geom = Column('geom', Geometry('POINT', 4326))

    def __repr__(self):
        return format_sqlobject_repr(self)


class GenericNumericalValue(Base):
    """
    An object used to map the 'generique' table of the
    RSESQ database.
    """
    __tablename__ = 'generique'
    __table_args__ = ({"schema": "resultats"})

    gen_num_value_id = Column('generic_res_id', Integer, primary_key=True)
    gen_num_value = Column('valeur_num', Float)
    # Relation with table resultats.observation
    observation_uuid = Column('observation_uuid', UUID(as_uuid=True))
    # Relation with table librairies.xm_observed_property
    obs_property_id = Column('obs_property_id', Integer)
    gen_num_value_notes = Column('gen_note', String)

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
    sampling_feature_id = Column('elemcarac_id', Integer)
    # Relation with table librairies.elem_interest
    interest_id = Column('interet_id', String)
    loc_id = Column(Integer, ForeignKey('rsesq.localisation.loc_id'))

    __mapper_args__ = {'polymorphic_on': interest_id}

    def __repr__(self):
        return format_sqlobject_repr(self)


class ObservationWell(SamplingFeature):
    """
    An object used to map the observation wells of the RSESQ.
    """
    __mapper_args__ = {'polymorphic_identity': 1}
    obs_well_id = Column('elemcarac_nom', VARCHAR(length=250))
    obs_well_notes = Column('elemcarac_note', TEXT(length=None))


class ObservationWellStatistics(Base):
    """
    An object used to map the 'obs_well_statistics' materialized view in the
    RSESQ database.
    """
    __tablename__ = 'obs_well_statistics'
    __table_args__ = ({"schema": "resultats"})

    sampling_feature_uuid = Column(
        'sampling_feature_uuid', UUID(as_uuid=True), primary_key=True)
    last_date = Column('last_date', DateTime)
    first_date = Column('first_date', DateTime)
    mean_water_level = Column('mean_water_level', Float)


class Observation(Base):
    __tablename__ = 'observation'
    __table_args__ = ({"schema": "rsesq"})

    observation_uuid = Column('observation_uuid', String, primary_key=True)
    observation_id = Column('observation_id', Integer)
    sampling_feature_uuid = Column('elemcarac_uuid', String)
    process_uuid = Column('process_uuid', String)
    obs_datetime = Column('date_relv_hg', DateTime)
    # Relation with table librairies.lib_obs_parameter
    param_id = Column('param_id', Integer)

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


class Sondes(Base):
    __tablename__ = 'sonde_caracteristiques'
    __table_args__ = ({"schema": "metadonnees"})

    sonde_uuid = Column('no_sonde_uuid', UUID(as_uuid=True), primary_key=True)
    sonde_serial_no = Column('no_sonde', String)
    date_reception = Column('date_reception', DateTime)
    date_withdrawal = Column('date_retrait', DateTime)
    in_repair = Column('en_reparation', Boolean)
    out_of_order = Column('hors_service', Boolean)
    lost = Column('perdue', Boolean)
    off_network = Column('hors_reseau', Boolean)
    sonde_notes = Column('remarque', String)

    sonde_model_id = Column(
        'instrument_id', Integer,
        ForeignKey('librairies.lib_instrument_mddep.instrument_id'))


class SondeInstallations(Base):
    __tablename__ = 'sonde_installation'
    __table_args__ = ({"schema": "processus"})

    installation_id = Column('deploiement_id', String, primary_key=True)
    logger_id = Column('no_sonde', String)
    obs_well_id = Column('no_piezometre', String)


class SondeModels(Base):
    __tablename__ = 'lib_instrument_mddep'
    __table_args__ = ({"schema": "librairies"})

    sonde_model_id = Column('instrument_id', Integer, primary_key=True)
    sonde_brand = Column('instrument_marque', String)
    sonde_model = Column('instrument_model', String)


class TimeSeriesChannels(Base):
    __tablename__ = 'canal_temporel'
    __table_args__ = ({"schema": "resultats"})

    channel_uuid = Column('canal_uuid', String, primary_key=True)
    channel_id = Column('canal_id', Integer)
    observation_uuid = Column('observation_uuid', String)
    # Relation with table librairies.xm_observed_property
    obs_property_id = Column('obs_property_id', Integer)

    def __repr__(self):
        return format_sqlobject_repr(self)


class TimeSeriesData(Base):
    __tablename__ = 'temporel_corrige'
    __table_args__ = ({"schema": "resultats"})

    datetime = Column('date_heure', DateTime, primary_key=True)
    value = Column('valeur', Float, primary_key=True)
    # Relation with table resultats.canal_temporel
    channel_id = Column('canal_id', Integer, primary_key=True)


# =============================================================================
# ---- Accessor
# =============================================================================
class DatabaseAccessorRSESQ(DatabaseAccessor):
    """
    Manage the connection and requests to a RSESQ database.
    """

    def __init__(self, database, username, password, hostname, port,
                 client_encoding='utf8'):
        super().__init__()
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

    # --- Indexes
    def _create_index(self, name):
        """
        Return a new index that can be used subsequently to add a new item
        related to name in the database.

        Note that you need to take into account temporary indexes that might
        have been requested by the database manager but haven't been
        commited yet to the database.
        """
        if name in ['observation_wells_data', 'sondes_data']:
            return uuid.uuid4()
        elif name == 'manual_measurements':
            max_commited_id = (
                self._session.query(
                    func.max(GenericNumericalValue.gen_num_value_id))
                .one())[0]
            return max(self.temp_indexes(name) + [max_commited_id]) + 1
        else:
            raise NotImplementedError

    # ---- Locations
    def _get_location(self, loc_id):
        """
        Return the sqlalchemy Location object corresponding to the
        specified location ID.
        """
        location = (
            self._session.query(Location)
            .filter(Location.loc_id == loc_id)
            .one()
            )
        return location

    # ---- Observation Wells
    def _get_obs_well_sampling_feature_uuid(self, obs_well_id):
        """
        Return the sampling feature UUID corresponding the the observation
        well common ID that is used to reference the well in the monitoring
        network (not the database).
        """
        sampling_feature_uuid = (
            self._session.query(ObservationWell.sampling_feature_uuid)
            .filter(ObservationWell.obs_well_id == obs_well_id)
            .one()
            .sampling_feature_uuid
            )
        return sampling_feature_uuid

    def _get_observation_well(self, sampling_feature_uuid):
        """
        Return the sqlalchemy ObservationWell object corresponding to the
        specified sampling feature UUID.
        """
        obs_well = (
            self._session.query(ObservationWell)
            .filter(ObservationWell.sampling_feature_uuid ==
                    sampling_feature_uuid)
            .one()
            )
        return obs_well

    def _create_observation_wells_statistics(self):
        """
        Create a materialized view where statistics related to the water level
        data acquired in the observation wells of the monitoring network are
        saved.
        """
        select_query = (
            self._session.query(Observation.sampling_feature_uuid
                                .label('sampling_feature_uuid'),
                                func.max(TimeSeriesData.datetime)
                                .label('last_date'),
                                func.min(TimeSeriesData.datetime)
                                .label('first_date'),
                                func.avg(TimeSeriesData.value)
                                .label('mean_water_level'))
            .filter(Observation.observation_uuid ==
                    TimeSeriesChannels.observation_uuid)
            .filter(TimeSeriesData.channel_id ==
                    TimeSeriesChannels.channel_id)
            .filter(TimeSeriesChannels.obs_property_id == 2)
            .group_by(Observation.sampling_feature_uuid)
            )
        select_statement = str(select_query.statement.compile(
            self._engine, compile_kwargs={"literal_binds": True}))
        self.execute(
            "CREATE MATERIALIZED VIEW resultats.obs_well_statistics AS " +
            select_statement)
        self.execute(
            "CREATE UNIQUE INDEX obs_well_statistics_index ON "
            "resultats.obs_well_statistics(sampling_feature_uuid)")

    def _refresh_observation_wells_statistics(self):
        """
        Refresh the materialized view containing statistics about the
        water level data.
        """
        if not self._engine.dialect.has_table(
                self._connection, 'obs_well_statistics', schema='resultats'):
            self.create_observation_wells_statistics()
        else:
            self.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY "
                         "resultats.obs_well_statistics")

    def get_observation_wells_statistics(self):
        """
        Return a :class:`pandas.DataFrame` containing statistics related to
        the water level data acquired in the observation wells of the
        monitoring network.
        """
        # Create a materialized view containing the statistics if it
        # doesn't exists. Calculation of these statistics take about
        # 10 seconds locally, so we are caching the results in a
        # materialized view and only refresh it when really needed.
        if not self._engine.dialect.has_table(
                self._connection, 'obs_well_statistics', schema='resultats'):
            self._create_observation_wells_statistics()

        # Fetch data from the materialized view.
        query = self._session.query(ObservationWellStatistics)
        data = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True)
        data.set_index('sampling_feature_uuid', inplace=True, drop=True)

        # We drop the time from the datetime since we don't need it.
        data['last_date'] = data['last_date'].dt.date
        data['first_date'] = data['first_date'].dt.date

        # Round mean value.
        data['mean_water_level'] = data['mean_water_level'].round(decimals=3)

        return data

    def add_observation_wells_data(self, sampling_feature_uuid,
                                   attribute_values):
        """
        Add a new observation well to the database using the provided ID
        and attribute values.
        """
        # We need first to create a new location in table rsesq.localisation.
        new_loc_id = (
            self._session.query(func.max(Location.loc_id))
            .one())
        new_loc_id = new_loc_id[0] + 1
        location = Location(loc_id=new_loc_id)
        self._session.add(location)

        # We then add the new observation well.
        new_sampling_feature_id = (
            self._session.query(func.max(SamplingFeature.sampling_feature_id))
            .one())
        new_sampling_feature_id = new_sampling_feature_id[0] + 1

        obs_well = ObservationWell(
            sampling_feature_uuid=sampling_feature_uuid,
            sampling_feature_id=new_sampling_feature_id,
            interest_id=1,
            loc_id=new_loc_id
            )
        self._session.add(obs_well)

        # We then set the attribute values provided in argument for this
        # new observation well if any.
        for attribute_name, attribute_value in attribute_values.items():
            self.set_observation_wells_data(
                sampling_feature_uuid,
                attribute_name,
                attribute_value,
                auto_commit=False)
        self._session.commit()

    def set_observation_wells_data(self, sampling_feature_id, attribute_name,
                                   attribute_value, auto_commit=True):
        """
        Save in the database the new attribute value for the observation well
        corresponding to the specified sampling feature ID.
        """
        obs_well = self._get_observation_well(sampling_feature_id)

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
            obs_well.obs_well_notes = r' || '.join(notes)
        elif attribute_name in ['latitude', 'longitude']:
            location = self._get_location(obs_well.loc_id)
            setattr(location, attribute_name, attribute_value)

            # We also need to update the postgis geometry object for the
            # location.
            if (location.longitude is not None and
                    location.latitude is not None):
                location.loc_geom = WKTElement(
                    'POINT({} {})'.format(location.longitude,
                                          location.latitude),
                    srid=4326)
        elif attribute_name in ['municipality']:
            location = self._get_location(obs_well.loc_id)
            location.loc_notes = (
                ' || municipalité : {}'.format(attribute_value))

        # Commit changes to the BD.
        if auto_commit:
            self._session.commit()

    def get_observation_wells_data(self):
        """
        Return a :class:`pandas.DataFrame` containing the information related
        to the observation wells that are saved in the database.
        """
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
        obs_wells.set_index(
            'sampling_feature_uuid', inplace=True, drop=True)

        # Replace nan by None.
        obs_wells = obs_wells.where(obs_wells.notnull(), None)

        return obs_wells

    # ---- Sonde Brands and Models Library
    def _get_sonde(self, sonde_id):
        """
        Return the sqlalchemy Sondes object corresponding to the
        specified sonde ID.
        """
        sonde = (
            self._session.query(Sondes)
            .filter(Sondes.sonde_uuid == sonde_id)
            .one()
            )
        return sonde

    def get_sonde_models_lib(self):
        """
        Return a :class:`pandas.DataFrame` containing the information related
        to sonde brands and models.
        """
        query = (
            self._session.query(SondeModels)
            .order_by(SondeModels.sonde_brand,
                      SondeModels.sonde_model)
            ).with_labels()
        sonde_models = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True)

        # Rename the column names to that expected by the api.
        columns_map = map_table_column_names(SondeModels, with_labels=True)
        sonde_models.rename(columns_map, axis='columns', inplace=True)

        # Combine the brand and model into a same field.
        sonde_models['sonde_brand_model'] = (
            sonde_models[['sonde_brand', 'sonde_model']]
            .apply(lambda x: ' '.join(x), axis=1))

        # Set the index to the observation well ids.
        sonde_models.set_index('sonde_model_id', inplace=True, drop=True)

        return sonde_models

    # ---- Sondes Inventory
    def add_sondes_data(self, sonde_uuid, attribute_values):
        """
        Add a new sonde to the database using the provided sonde ID
        and attribute values.
        """
        # We now create a new measurement in table 'resultats.generique'.
        sonde = Sondes(
            sonde_uuid=sonde_uuid,
            sonde_serial_no=attribute_values.get('sonde_serial_no', ''),
            date_reception=attribute_values.get('date_reception', None),
            date_withdrawal=attribute_values.get('date_withdrawal', None),
            in_repair=attribute_values.get('in_repair', None),
            out_of_order=attribute_values.get('out_of_order', None),
            lost=attribute_values.get('lost', None),
            off_network=attribute_values.get('off_network', None),
            sonde_notes=attribute_values.get('sonde_notes', None),
            sonde_model_id=attribute_values.get('sonde_notes', None),
            )
        self._session.add(sonde)
        self._session.commit()

    def get_sondes_data(self):
        """
        Return a :class:`pandas.DataFrame` containing the information related
        to the sondes used to monitor groundwater properties in the wells.
        """
        query = (
            self._session.query(Sondes)
            .order_by(Sondes.sonde_model_id,
                      Sondes.sonde_serial_no)
            ).with_labels()
        sondes = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True)

        # Rename the column names to that expected by the api.
        columns_map = map_table_column_names(
            Sondes, SondeModels, with_labels=True)
        sondes.rename(columns_map, axis='columns', inplace=True)

        # Strip timezone info since it is not set correctly in the
        # BD anyway.
        sondes['date_reception'] = (
            sondes['date_reception'].dt.tz_localize(None))
        sondes['date_withdrawal'] = (
            sondes['date_withdrawal'].dt.tz_localize(None))

        # Strip the hour portion since it doesn't make sense here.
        sondes['date_reception'] = sondes['date_reception'].dt.date
        sondes['date_withdrawal'] = sondes['date_withdrawal'].dt.date

        # Set the index to the observation well ids.
        sondes.set_index('sonde_uuid', inplace=True, drop=True)

        return sondes

    def set_sondes_data(self, sonde_id, attribute_name, attribute_value):
        """
        Save in the database the new attribute value for the sonde
        corresponding to the specified sonde UID.
        """
        sonde = self._get_sonde(sonde_id)
        setattr(sonde, attribute_name, attribute_value)
        self._session.commit()

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
                'TEMP_EAU': 'red',
                'COND_ELEC': 'cyan'
                }[monitored_property]

    # ---- Timeseries
    def get_timeseries_for_obs_well(self, sampling_feature_uuid,
                                    monitored_property):
        """
        Return a :class:`TimeSeriesGroup` object containing the
        :class:`TimeSeries` objects holding the data acquired for the
        specified monitored property in the observation well corresponding
        to the specified sampling feature ID. .
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

        # Define a query to fetch the timseries data from the database.
        query = (
            self._session.query(TimeSeriesData.value,
                                TimeSeriesData.datetime,
                                TimeSeriesData.channel_id)
            .filter(TimeSeriesChannels.obs_property_id == obs_property_id)
            .filter(Observation.sampling_feature_uuid == sampling_feature_uuid)
            .filter(Observation.observation_uuid ==
                    TimeSeriesChannels.observation_uuid)
            .filter(TimeSeriesData.channel_id == TimeSeriesChannels.channel_id)
            .order_by(TimeSeriesData.datetime, TimeSeriesData.channel_id)
            ).with_labels()

        # Fetch the data from the database and store them in a pandas
        # Series using datetimes as index.
        data = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True)
        columns_map = map_table_column_names(
            Observation, TimeSeriesChannels, TimeSeriesData, with_labels=True)
        data.rename(columns_map, axis='columns', inplace=True)

        data['datetime'] = pd.to_datetime(
            data['datetime'], format="%Y-%m-%d %H:%M:%S")

        # For each channel, store the data in a time series object and
        # add it to the monitored property object.
        tseries_group = TimeSeriesGroup(
            monitored_property,
            self.get_monitored_property_name(monitored_property),
            self.get_monitored_property_units(monitored_property),
            yaxis_inverted=(monitored_property == 'NIV_EAU')
            )

        # Check for duplicates along the time axis and drop the duplicated
        # entries if any.
        duplicated = data.duplicated(subset='datetime')
        nbr_duplicated = len(duplicated[duplicated])
        if nbr_duplicated:
            print(("Warning: {} duplicated {} entrie(s) were found while "
                   "fetching these data."
                   ).format(nbr_duplicated, monitored_property))
            data.drop_duplicates(subset='datetime', inplace=True)
        tseries_group.nbr_duplicated = nbr_duplicated

        # Set the index.
        data.set_index(['datetime'], drop=True, inplace=True)

        # Split the data in channels.
        for channel_id in data['channel_id'].unique():
            channel_data = data[data['channel_id'] == channel_id]
            tseries_group.add_timeseries(TimeSeries(
                pd.Series(channel_data['value'], index=channel_data.index),
                tseries_id=channel_id,
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
            print(p)
            raise p

    # ---- Manual mesurements
    def add_manual_measurements(self, gen_num_value_id, attribute_values):
        """
        Add a new manual measurements to the database using the provided ID
        and attribute values.
        """
        # We need first to create a new observation in table rsesq.observation.
        new_observation_id = (
            self._session.query(func.max(Observation.observation_id))
            .one())
        new_observation_id = new_observation_id[0] + 1

        observation = Observation(
            observation_uuid=uuid.uuid4(),
            observation_id=new_observation_id,
            sampling_feature_uuid=attribute_values.get(
                'sampling_feature_uuid', None),
            process_uuid=None,
            obs_datetime=attribute_values.get('datetime', None),
            param_id=4
            )
        self._session.add(observation)

        # We now create a new measurement in table 'resultats.generique'.
        measurement = GenericNumericalValue(
            gen_num_value_id=gen_num_value_id,
            gen_num_value=attribute_values.get('value', None),
            observation_uuid=observation.observation_uuid,
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
        # Define a query to fetch the water level manual measurements
        # from the database.
        query = (
            self._session.query(
                GenericNumericalValue.gen_num_value.label('value'),
                GenericNumericalValue.gen_num_value_notes.label('notes'),
                GenericNumericalValue.gen_num_value_id,
                Observation.obs_datetime.label('datetime'),
                Observation.sampling_feature_uuid)
            .filter(GenericNumericalValue.obs_property_id == 2)
            .filter(GenericNumericalValue.observation_uuid ==
                    Observation.observation_uuid)
            .order_by(GenericNumericalValue.gen_num_value_id)
            ).with_labels()
        measurements = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True)

        # Rename the column names to that expected by the api.
        columns_map = map_table_column_names(
            GenericNumericalValue, Observation, with_labels=True)
        measurements.rename(columns_map, axis='columns', inplace=True)

        # Set the index to the observation well ids.
        measurements.set_index('gen_num_value_id', inplace=True, drop=True)

        return measurements

    def set_manual_measurements(self, gen_num_value_id, attribute_name,
                                attribute_value):
        """
        Save in the database the new attribute value for the manual
        measurement corresponding to the specified id.
        """
        measurement = (
            self._session.query(GenericNumericalValue)
            .filter(GenericNumericalValue.gen_num_value_id == gen_num_value_id)
            .one()
            )
        if attribute_name == 'sampling_feature_uuid':
            observation = self._get_observation(measurement.observation_uuid)
            observation.sampling_feature_uuid = attribute_value
        elif attribute_name == 'datetime':
            observation = self._get_observation(measurement.observation_uuid)
            observation.obs_datetime = attribute_value
        elif attribute_name == 'value':
            measurement.gen_num_value = float(attribute_value)
        elif attribute_name == 'notes':
            measurement.gen_num_value_notes = attribute_value
        self._session.commit()

    # ---- Private methods
    def _get_observation(self, observation_uuid):
        """
        Return the observation related to the given uuid.
        """
        return (self._session.query(Observation)
                .filter(Observation.observation_uuid == observation_uuid)
                .one())


if __name__ == "__main__":
    from sardes.config.database import get_dbconfig

    dbconfig = get_dbconfig('rsesq_postgresql')
    accessor = DatabaseAccessorRSESQ(**dbconfig)

    accessor.connect()
    obs_wells = accessor.get_observation_wells_data()
    sonde_data = accessor.get_sondes_data()
    sonde_models = accessor.get_sonde_models_lib()
    manual_measurements = accessor.get_manual_measurements()

    sampling_feature_uuid = accessor._get_obs_well_sampling_feature_uuid(
        '01030001')
    wlevel = accessor.get_timeseries_for_obs_well(
        sampling_feature_uuid, 'NIV_EAU').timeseries[0]

    accessor.close_connection()
