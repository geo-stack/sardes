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
from geoalchemy2 import Geometry
from geoalchemy2.elements import WKTElement
import pandas as pd
from sqlalchemy import create_engine, extract, func
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.inspection import inspect
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.types import TEXT, VARCHAR, Boolean

# ---- Local imports
from sardes.api.database_accessor import DatabaseAccessor
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

    loc_common_name = Column('nom_communn', String)
    latitude = Column('latitude_8', Float)
    longitude = Column(Float)
    is_station_active = Column('station_active', Boolean)
    loc_notes = Column('remarque', String)
    loc_id = Column(String, primary_key=True)
    loc_geom = Column('geom', Geometry('POINT', 4326))

    def __repr__(self):
        return format_sqlobject_repr(self)


class ManualMeasurements(Base):
    """
    An object used to map the 'manual measurements' table of the
    RSESQ database.
    """
    __tablename__ = 'generique'
    __table_args__ = ({"schema": "resultats"})

    manual_measurement_id = Column('generic_res_id', Integer, primary_key=True)
    obs_well_id = Column('no_piezometre', String)
    manual_measurement_date = Column('la_date', DateTime)
    manual_measurement_time = Column('heure', DateTime)
    manual_measurement = Column('lecture_profondeur', Float)

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

    def __repr__(self):
        return format_sqlobject_repr(self)


class ObservationWell(SamplingFeature):
    """
    An object used to map the observation wells of the RSESQ.
    """
    __mapper_args__ = {'polymorphic_identity': 1}
    obs_well_id = Column('elemcarac_nom', VARCHAR(length=250))
    obs_well_notes = Column('elemcarac_note', TEXT(length=None))


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

    def set_observation_wells_data(self, sampling_feature_id, attribute_name,
                                   attribute_value):
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
            label = [
                'nom_commu', 'aquifere', 'nappe', 'code_aqui', 'zone_rechar',
                'influences', 'station_active', 'remarque'][index]

            notes = [n.strip() for n in obs_well.obs_well_notes.split(r'||')]
            notes[index] = '{}: {}'.format(label, attribute_value)
            obs_well.obs_well_notes = r' || '.join(notes)
        elif attribute_name in ['latitude', 'longitude']:
            location = self._get_location(obs_well.loc_id)
            setattr(location, attribute_name, attribute_value)

            # We also need to update the postgis geometry object for the
            # location.
            location.loc_geom = WKTElement(
                'POINT({} {})'.format(location.longitude, location.latitude),
                srid=4326)
        elif attribute_name in ['municipality']:
            location = self._get_location(obs_well.loc_id)
            location.loc_notes = (
                ' || municipalité : {}'.format(attribute_value))

        # Commit changes to the BD.
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
    def get_sondes_data(self):
        """
        Return a :class:`pandas.DataFrame` containing the information related
        to the sondes used to monitor groundwater properties in the wells.
        """
        query = (
            self._session.query(Sondes)
            .filter(SondeModels.sonde_model_id == Sondes.sonde_model_id)
            .order_by(SondeModels.sonde_brand,
                      SondeModels.sonde_model,
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
                'TEMP': 'red',
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
            self._session.query(TimeSeriesRaw.value,
                                TimeSeriesRaw.datetime,
                                TimeSeriesRaw.channel_uuid)
            .filter(Observation.sampling_feature_uuid == sampling_feature_uuid)
            .filter(Observation.observation_uuid ==
                    TimeSeriesChannels.observation_uuid)
            .filter(TimeSeriesChannels.obs_property_id == obs_property_id)
            .filter(TimeSeriesRaw.channel_uuid ==
                    TimeSeriesChannels.channel_uuid)
            .order_by(TimeSeriesRaw.datetime, TimeSeriesRaw.channel_uuid)
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

    # ---- Manual mesurements
    def get_manual_measurements(self):
        """
        Return a :class:`pandas.DataFrame` containing the water level manual
        measurements made in the observation wells for the entire monitoring
        network.
        """
        # Define a query to fetch the timseries data from the database.
        query = (
            self._session.query(ManualMeasurements,
                                ObservationWell.sampling_feature_uuid)
            .filter(ManualMeasurements.obs_well_id ==
                    ObservationWell.obs_well_id)
            .order_by(ManualMeasurements.obs_well_id,
                      ManualMeasurements.manual_measurement_date,
                      ManualMeasurements.manual_measurement_time)
            ).with_labels()
        measurements = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True)

        # Rename the column names to that expected by the api.
        columns_map = map_table_column_names(
            ManualMeasurements, ObservationWell, with_labels=True)
        measurements.rename(columns_map, axis='columns', inplace=True)

        # Strip timezone info since it is not set correctly in the
        # BD anyway.
        measurements['manual_measurement_date'] = (
            measurements['manual_measurement_date'].dt.tz_localize(None))
        measurements['manual_measurement_time'] = (
            measurements['manual_measurement_time'].dt.tz_localize(None))

        # Join the date and hour into a single datetime column.
        measurements['datetime'] = pd.to_datetime(
            measurements['manual_measurement_date'].dt.date.astype(str) +
            ' ' +
            measurements['manual_measurement_time'].dt.time.astype(str))

        # Drop the columns that are not required by the API.
        measurements.drop(['manual_measurement_date',
                           'manual_measurement_time',
                           'obs_well_id'],
                          axis=1, inplace=True)

        # Set the index to the observation well ids.
        measurements.set_index(
            'manual_measurement_id', inplace=True, drop=True)
        return measurements


if __name__ == "__main__":
    from sardes.config.database import get_dbconfig

    dbconfig = get_dbconfig('rsesq_postgresql')
    accessor = DatabaseAccessorRSESQ(**dbconfig)

    accessor.connect()
    obs_wells = accessor.get_observation_wells_data()
    manual_measurements = accessor.get_manual_measurements()

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
