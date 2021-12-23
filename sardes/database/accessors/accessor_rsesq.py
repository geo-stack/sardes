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
import datetime
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
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.types import TEXT, VARCHAR, Boolean

# ---- Local imports
from sardes.api.database_accessor import DatabaseAccessor
from sardes.database.utils import map_table_column_names, format_sqlobject_repr
from sardes.api.timeseries import DataType


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
    loc_id = Column(Integer, primary_key=True)
    loc_geom = Column('geom', Geometry('POINT', 4326))

    def __repr__(self):
        return format_sqlobject_repr(self)


class Repere(Base):
    """
    An object used to map the 'Repere' table of the RSESQ database.
    """
    __tablename__ = 'repere'
    __table_args__ = ({"schema": "rsesq"})

    repere_uuid = Column('repere_uuid', UUID(as_uuid=True), primary_key=True)
    sampling_feature_uuid = Column(
        'elemcarac_uuid',
        UUID(as_uuid=True),
        ForeignKey('rsesq.elements_caracteristique.elemcarac_uuid',
                   ondelete='CASCADE'))
    top_casing_alt = Column('alt_hors_sol', Float)
    casing_length = Column('longueur_hors_sol', Float)
    start_date = Column('date_debut', DateTime)
    end_date = Column('date_fin', DateTime)
    is_alt_geodesic = Column('elevation_geodesique', Boolean)
    repere_note = Column('repere_note', String(250))

    def __repr__(self):
        return format_sqlobject_repr(self)


class GenericNumericalValue(Base):
    """
    An object used to map the 'generique' table of the
    RSESQ database.
    """
    __tablename__ = 'generique'
    __table_args__ = ({"schema": "resultats"})

    gen_num_value_id = Column('generic_res_id', Integer)
    gen_num_value_uuid = Column(
        'generic_res_uuid', UUID(as_uuid=True), primary_key=True)
    gen_num_value = Column('valeur_num', Float)
    # Relation with table resultats.observation
    observation_uuid = Column('observation_uuid', UUID(as_uuid=True))
    obs_property_id = Column(
        'obs_property_id',
        Integer,
        ForeignKey('librairies.xm_observed_property.obs_property_id'))
    gen_num_value_notes = Column('gen_note', String)
    gen_init_num_value = Column('valeur_initial', String)

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
    interest_id = Column(
        'interet_id', Integer,
        ForeignKey('librairies.elem_interest.interet_id'))
    loc_id = Column(Integer, ForeignKey('rsesq.localisation.loc_id'))

    __mapper_args__ = {'polymorphic_on': interest_id}

    def __repr__(self):
        return format_sqlobject_repr(self)


class SamplingFeatureTypes(Base):
    """
    An object used to map the 'elem_interest' library of the
    RSESQ database.
    """
    __tablename__ = 'elem_interest'
    __table_args__ = ({"schema": "librairies"})

    sampling_feature_type_id = Column('interet_id', Integer, primary_key=True)
    sampling_feature_type_desc = Column('interet_desc', String)
    sampling_feature_type_abb = Column('interet_abb', String)

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

    observation_uuid = Column(
        'observation_uuid', UUID(as_uuid=True), primary_key=True)
    observation_id = Column('observation_id', Integer)
    obs_datetime = Column('date_relv_hg', DateTime)
    sampling_feature_uuid = Column(
        'elemcarac_uuid', UUID(as_uuid=True),
        ForeignKey('rsesq.elements_caracteristique.elemcarac_uuid'))
    process_uuid = Column(
        'process_uuid', UUID(as_uuid=True),
        ForeignKey('processus.processus.process_uuid'))
    # Foreign key with 'librairies.lib_obs_parameter.param_id'
    param_id = Column('param_id', Integer)

    def __repr__(self):
        return format_sqlobject_repr(self)


class ObservationType(Base):
    __tablename__ = 'lib_obs_parameter'
    __table_args__ = ({"schema": "librairies"})

    obs_type_id = Column('param_id', Integer, primary_key=True)
    obs_type_abb = Column('param_abb', String)
    obs_type_desc = Column('param_descr', String)


class ObservationProperty(Base):
    __tablename__ = 'xm_observed_property'
    __table_args__ = ({"schema": "librairies"})

    obs_property_id = Column('obs_property_id', Integer, primary_key=True)
    obs_property_name = Column('observed_property', String)
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


class SondeInstallation(Base):
    """
    An object used to map the 'processus.sonde_pompe_installation' table
    of the RSESQ database.
    """
    __tablename__ = 'sonde_pompe_installation'
    __table_args__ = ({"schema": "processus"})

    install_id = Column('deploiement_id', Integer, primary_key=True)
    install_uuid = Column('deploiement_uuid', UUID(as_uuid=True))
    sonde_serial_no = Column('no_sonde', String)
    start_date = Column('date_debut', DateTime)
    end_date = Column('date_fin', DateTime)
    install_depth = Column('profondeur', Float)
    sampling_feature_uuid = Column('elemcarac_uuid', UUID(as_uuid=True))
    operator = Column('operateur', String)


class SondeModels(Base):
    __tablename__ = 'lib_instrument_mddep'
    __table_args__ = ({"schema": "librairies"})

    sonde_model_id = Column('instrument_id', Integer, primary_key=True)
    sonde_brand = Column('instrument_marque', String)
    sonde_model = Column('instrument_model', String)


class Processes(Base):
    __tablename__ = 'processus'
    __table_args__ = ({"schema": "processus"})

    process_type = Column('process_type', String)
    process_id = Column('process_id', Integer)
    process_uuid = Column('process_uuid', UUID(as_uuid=True), primary_key=True)


class ProcessesInstalls(Base):
    __tablename__ = 'processus_deploiement'
    __table_args__ = ({"schema": "processus"})

    process_id = Column('process_id', Integer)
    install_id = Column(
        'deploiement_id', Integer,
        ForeignKey('processus.sonde_pompe_installation.deploiement_id'))
    process_uuid = Column(
        'process_uuid', UUID(as_uuid=True),
        ForeignKey('processus.processus.process_uuid'),
        primary_key=True)


class TimeSeriesChannels(Base):
    """
    An object used to map the 'resultats.canal_temporel' table
    of the RSESQ database.
    """
    __tablename__ = 'canal_temporel'
    __table_args__ = ({"schema": "resultats"})

    channel_uuid = Column('canal_uuid', String, primary_key=True)
    channel_id = Column('canal_id', Integer)
    observation_uuid = Column(
        'observation_uuid', String,
        ForeignKey('rsesq.observation.observation_uuid'))
    obs_property_id = Column(
        'obs_property_id', Integer,
        ForeignKey('librairies.xm_observed_property.obs_property_id'))

    def __repr__(self):
        return format_sqlobject_repr(self)


class TimeSeriesData(Base):
    """
    An object used to map the 'resultats.temporel_corrige' table
    of the RSESQ database.
    """
    __tablename__ = 'temporel_corrige'
    __table_args__ = ({"schema": "resultats"})

    datetime = Column('date_heure', DateTime, primary_key=True)
    value = Column('valeur', Float)
    channel_id = Column(
        'canal_id', Integer,
        ForeignKey('resultats.canal_temporel.canal_id', ondelete='CASCADE',
                   onupdate='CASCADE'),
        primary_key=True,)

    @hybrid_property
    def dateyear(self):
        return self.datetime.year

    @dateyear.expression
    def dateyear(cls):
        return extract('year', TimeSeriesData.datetime)


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

    def _get_observation_wells_data_overview(self):
        """
        Return a :class:`pandas.DataFrame` containing an overview of
        the water level data that are available for each observation well
        of the monitoring network.
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

    def _get_observation_wells_data(self):
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
        obs_wells['aquifer_code'] = obs_wells['aquifer_code'].astype(float)

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

    # ---- Repere
    def add_repere_data(self, repere_id, attribute_values):
        """
        Add a new observation well repere data to the database using the
        provided repere ID and attribute values.
        """
        # We create a new repere item.
        repere = Repere(repere_uuid=repere_id)
        self._session.add(repere)

        # We then set the attribute values for this new installation.
        for name, value in attribute_values.items():
            setattr(repere, name, value)

        self._session.commit()

    def set_repere_data(self, repere_id, attribute_name, attribute_value,
                        auto_commit=True):
        """
        Save in the database the new attribute value for the observation well
        repere data corresponding to the specified ID.
        """
        repere = repere = (
            self._session.query(Repere)
            .filter(Repere.repere_uuid == repere_id)
            .one()
            )

        setattr(repere, attribute_name, attribute_value)
        if auto_commit:
            self._session.commit()

    def _get_repere_data(self):
        query = (
            self._session.query(Repere)
            ).with_labels()
        repere = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True)

        # Rename the column names to that expected by the api.
        columns_map = map_table_column_names(
            Repere, with_labels=True)
        repere.rename(columns_map, axis='columns', inplace=True)

        # Set the index to the observation well ids.
        repere.set_index('repere_uuid', inplace=True, drop=True)

        return repere

    # ---- Sonde Brands and Models Library
    def _get_sonde_models_lib(self):
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
            sonde_model_id=attribute_values.get('sonde_model_id', None),
            )
        self._session.add(sonde)
        self._session.commit()

    def _get_sondes_data(self):
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

        # Set the index to the sonde ids.
        sondes.set_index('sonde_uuid', inplace=True, drop=True)

        return sondes

    def set_sondes_data(self, sonde_id, attribute_name, attribute_value,
                        auto_commit=True):
        """
        Save in the database the new attribute value for the sonde
        corresponding to the specified sonde UID.
        """
        sonde = self._get_sonde(sonde_id)
        setattr(sonde, attribute_name, attribute_value)
        if auto_commit:
            self._session.commit()

    # ---- Sonde installations
    def _get_sonde_installation(self, install_id_or_uuid):
        """
        Return the sqlalchemy SondeInstallation object corresponding to the
        specified sonde ID.
        """
        if isinstance(install_id_or_uuid, int):
            sonde_installation = (
                self._session.query(SondeInstallation)
                .filter(SondeInstallation.install_id == install_id_or_uuid)
                .one()
                )
        else:
            sonde_installation = (
                self._session.query(SondeInstallation)
                .filter(SondeInstallation.install_uuid == install_id_or_uuid)
                .one()
                )
        return sonde_installation

    def add_sonde_installations(self, new_install_uuid, attribute_values):
        """
        Add a new sonde installation to the database using the provided ID
        and attribute values.
        """
        # We create a new sonde installation.
        new_install_id = (
            self._session.query(
                func.max(SondeInstallation.install_id))
            .one())[0] + 1
        new_process_uuid = uuid.uuid4()

        sonde_installation = SondeInstallation(
            install_id=new_install_id,
            install_uuid=new_install_uuid)
        self._session.add(sonde_installation)

        # We then set the attribute values for this new installation.
        for name, value in attribute_values.items():
            self.set_sonde_installations(
                new_install_uuid, name, value, auto_commit=False)

        # Add the new process to table processus.processus_deploiement. A new
        # entry will then be automatically added to table processus.processus.
        new_process_id = (
            self._session.query(
                func.max(Processes.process_id))
            .one())[0] + 1
        new_process_uuid = uuid.uuid4()

        new_process_install = ProcessesInstalls(
            process_id=new_process_id,
            install_id=new_install_id,
            process_uuid=new_process_uuid
            )
        self._session.add(new_process_install)

        # Input the process type for the new process that was automatically
        # generated.
        process = (
            self._session.query(Processes)
            .filter(Processes.process_uuid == new_process_uuid)
            .one()
            )
        process.process_type = 'sonde installation'

        # Commit changes to database.
        self._session.commit()

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

    def _get_sonde_installations(self):
        # Define the query to fetch the data.
        query = (
            self._session.query(
                SondeInstallation.install_uuid,
                SondeInstallation.start_date,
                SondeInstallation.end_date,
                SondeInstallation.install_depth,
                SondeInstallation.sampling_feature_uuid,
                SondeInstallation.sonde_serial_no)
            .filter(SondeInstallation.install_id ==
                    ProcessesInstalls.install_id)
            .filter(Processes.process_uuid == ProcessesInstalls.process_uuid)
            .filter(Processes.process_type == 'sonde installation')
            ).with_labels()
        data = pd.read_sql_query(
            query.statement, query.session.bind, coerce_float=True)

        # Rename the column names to that expected by the api.
        columns_map = map_table_column_names(
            SondeInstallation, Sondes, ProcessesInstalls, Processes,
            with_labels=True)
        data.rename(columns_map, axis='columns', inplace=True)

        # Set the index of the dataframe.
        data.set_index('install_uuid', inplace=True, drop=True)

        # Strip timezone info since it is not set correctly in the
        # BD anyway.
        data['start_date'] = data['start_date'].dt.tz_localize(None)
        data['end_date'] = data['end_date'].dt.tz_localize(None)

        # Replace sonde serial number with the corresponding sonde uuid.
        sondes_data = self.get('sondes_data')
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

    # ---- Observations
    def _get_observation_property_id(self, data_type):
        """
        Return the observation property ID for the given data type.
        """
        return {DataType.WaterLevel: 2,
                DataType.WaterTemp: 1,
                DataType.WaterEC: 3}[DataType(data_type)]

    def _get_observation(self, obs_id_or_uuid):
        """
        Return the observation related to the given uuid or id.
        """
        if isinstance(obs_id_or_uuid, uuid.UUID):
            return (self._session.query(Observation)
                    .filter(Observation.observation_uuid == obs_id_or_uuid)
                    .one())
        else:
            return (self._session.query(Observation)
                    .filter(Observation.observation_id == obs_id_or_uuid)
                    .one())

    def _get_monitored_property_name(self, monitored_property):
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

    def _get_observation_property(self, obs_property_id):
        """
        Return the sqlalchemy ObservationProperty object corresponding to the
        given ID.
        """
        return (
            self._session.query(ObservationProperty)
            .filter(ObservationProperty.obs_property_id == obs_property_id)
            .one())

    # ---- Timeseries
    def _get_sonde_id_from_obs_id(self, observation_id):
        """
        Return the sonde ID associated with the given observation ID.
        """
        return (
            self._session.query(SondeInstallation)
            .filter(Observation.observation_id == observation_id)
            .filter(Observation.process_uuid ==
                    ProcessesInstalls.process_uuid)
            .filter(ProcessesInstalls.install_id ==
                    SondeInstallation.install_id)
            .one()
            .sonde_serial_no)

    def _get_sonde_install_depth_from_obs_id(self, obs_id):
        """
        Return the installation depth of the sonde for the given
        observation ID.
        """
        try:
            return (
                self._session.query(SondeInstallation)
                .filter(Observation.observation_id == obs_id)
                .filter(Observation.process_uuid ==
                        ProcessesInstalls.process_uuid)
                .filter(ProcessesInstalls.install_id ==
                        SondeInstallation.install_id)
                .one()
                .install_depth)
        except NoResultFound:
            return None

    def get_timeseries_for_obs_well(self, sampling_feature_uuid, data_type):
        """
        Return a pandas dataframe containing the readings for the given
        data type and observation well.
        """
        data_type = DataType(data_type)

        # Get the observation property id that is used to reference in the
        # database the corresponding monitored property.
        obs_property_id = self._get_observation_property_id(data_type)
        obs_prop = self._get_observation_property(obs_property_id)

        # Define a query to fetch the timseries data from the database.
        query = (
            self._session.query(TimeSeriesData.value,
                                TimeSeriesData.datetime,
                                Observation.observation_id.label('obs_id'))
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
        data.rename(columns={'value': data_type}, inplace=True)

        data['sonde_id'] = None
        for obs_id in data['obs_id'].unique():
            sonde_id = self._get_sonde_id_from_obs_id(obs_id)
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

    def _get_timeseriesdata(self, date_time, obs_id_or_uuid, data_type):
        """
        Return the sqlalchemy TimeSeriesData object corresponding to a
        timeseries data of the database.
        """
        obs_property_id = self._get_observation_property_id(data_type)
        if isinstance(obs_id_or_uuid, uuid.UUID):
            observation_uuid = obs_id_or_uuid
        else:
            observation = self._get_observation(obs_id_or_uuid)
            observation_uuid = observation.observation_uuid
        return (
            self._session.query(TimeSeriesData)
            .filter(TimeSeriesChannels.obs_property_id == obs_property_id)
            .filter(TimeSeriesChannels.observation_uuid == observation_uuid)
            .filter(TimeSeriesData.channel_id ==
                    TimeSeriesChannels.channel_id)
            .filter(TimeSeriesData.datetime == date_time)
            .one()
            )

    def _query_timeseriesdata(self, date_times, obs_id, data_type):
        """
        Return the sqlalchemy TimeSeriesData object corresponding to a
        timeseries data of the database.
        """
        obs_property_id = self._get_observation_property_id(data_type)
        observation = self._get_observation(obs_id)
        return (
            self._session.query(TimeSeriesData)
            .filter(TimeSeriesChannels.obs_property_id == obs_property_id)
            .filter(TimeSeriesChannels.observation_uuid ==
                    observation.observation_uuid)
            .filter(TimeSeriesData.channel_id ==
                    TimeSeriesChannels.channel_id)
            .filter(TimeSeriesData.datetime.in_(date_times))
            )

    def _clean_observation_if_null(self, obs_id):
        """
        Delete observation with to the given ID from the database
        if it is empty.
        """
        observation = self._get_observation(obs_id)
        if observation.param_id == 7:
            count = (self._session.query(TimeSeriesData)
                     .filter(TimeSeriesChannels.observation_uuid ==
                             observation.observation_uuid)
                     .filter(TimeSeriesData.channel_id ==
                             TimeSeriesChannels.channel_id)
                     .count())
            if count == 0:
                print("Deleting observation {} because it is now empty."
                      .format(observation.observation_id))
                self._session.delete(observation)
                self._session.commit()

    def save_timeseries_data_edits(self, tseries_edits):
        """
        Save in the database a set of edits that were made to to timeseries
        data that were already saved in the database.
        """
        obs_uuid_stack = {}
        for (date_time, obs_id, data_type) in tseries_edits.index:
            if obs_id not in obs_uuid_stack:
                observation = self._get_observation(obs_id)
                obs_uuid_stack[obs_id] = observation.observation_uuid

            # Fetch the timeseries data orm object.
            tseries_data = self._get_timeseriesdata(
                date_time, obs_uuid_stack[obs_id], data_type)
            # Save the edited value.
            tseries_data.value = tseries_edits.loc[
                (date_time, obs_id, data_type), 'value']
        self._session.commit()

    def add_timeseries_data(self, tseries_data, obs_well_id,
                            sonde_installation_id=None):
        """
        Save in the database a set of timeseries data associated with the
        given well and sonde installation id.
        """
        # We create a new observation.
        sonde_installation = self._get_sonde_installation(
            sonde_installation_id)
        process_install = (
            self._session.query(ProcessesInstalls)
            .filter(ProcessesInstalls.install_id ==
                    sonde_installation.install_id)
            .one())
        new_obs_id = (
            self._session.query(
                func.max(Observation.observation_id))
            .one())[0] + 1
        new_observation = Observation(
            observation_uuid=uuid.uuid4(),
            observation_id=new_obs_id,
            sampling_feature_uuid=obs_well_id,
            process_uuid=process_install.process_uuid,
            obs_datetime=max(tseries_data['datetime']),
            param_id=7
            )
        self._session.add(new_observation)
        self._session.commit()

        date_times = list(pd.to_datetime(tseries_data['datetime']))
        for data_type in DataType:
            if data_type not in tseries_data.columns:
                continue

            new_tseries_channel_id = (
                self._session.query(
                    func.max(TimeSeriesChannels.channel_id))
                .one())[0] + 1
            new_tseries_channel = TimeSeriesChannels(
                channel_uuid=uuid.uuid4(),
                channel_id=new_tseries_channel_id,
                obs_property_id=self._get_observation_property_id(data_type),
                observation_uuid=new_observation.observation_uuid
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

    def execute(self, sql_request, **kwargs):
        """Execute a SQL statement construct and return a ResultProxy."""
        try:
            return self._connection.execute(sql_request, **kwargs)
        except ProgrammingError as p:
            print(p)
            raise p

    # ---- Manual mesurements
    def _get_generic_num_value(self, gen_num_value_id):
        """
        Return the sqlalchemy GenericNumericalValue object corresponding
        to the given ID.
        """
        generic_num_value = (
            self._session.query(GenericNumericalValue)
            .filter(GenericNumericalValue.gen_num_value_id == gen_num_value_id)
            .one()
            )
        return generic_num_value

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
        self._session.commit()

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

    def _get_manual_measurements(self):
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
        measurement = self._get_generic_num_value(gen_num_value_id)
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

    def _del_manual_measurements(self, gen_num_value_id):
        """
        Delete the manual measurement corresponding to the specified id from
        the database.
        """
        measurement = self._get_generic_num_value(gen_num_value_id)
        observation = self._get_observation(measurement.observation_uuid)
        # We only need to delete the observation since there is
        # ON DELETE CASCADE condition that is set in the database.
        self._session.delete(observation)
        self._session.commit()


# =============================================================================
# ---- Utilities
# =============================================================================
def test_duplicate_timeseries_data(accessor):
    """
    For each monitoring properties, check if there is more than one values
    saved in the database for each date.
    """
    varnames = [DataType.WaterLevel, DataType.WaterTemp, DataType.WaterEC]
    duplicate_count = {}
    duplicated_data = {}
    obs_wells = accessor.get('observation_wells_data')

    for var in varnames:
        print('Testing', var.name, 'for duplicate data...')
        duplicate_count[var] = []
        duplicated_data[var] = []

        for obs_well_uuid in obs_wells.index:
            tseries_group = accessor.get_timeseries_for_obs_well(
                obs_well_uuid, var)
            if tseries_group.nbr_duplicated > 0:
                duplicate_count[var].append(
                    (tseries_group.obs_well_id,
                     tseries_group.nbr_duplicated))
                duplicated_data[var].extend(tseries_group.duplicated_data)
    return duplicate_count, duplicated_data


def update_repere_table(filename, accessor):
    """
    Update the observation wells repere data in the database from an
    Excel file.
    """
    if accessor._engine.dialect.has_table(
            accessor._connection, 'repere', schema='rsesq'):
        Repere.__table__.drop(accessor._engine)
    Base.metadata.create_all(accessor._engine, tables=[Repere.__table__])

    obs_wells = accessor.get('observation_wells_data')
    repere_data = pd.read_excel(filename)
    for row in range(len(repere_data)):
        row_data = repere_data.iloc[row]
        date_debut = row_data['date_debut']
        heure_debut = row_data['heure_debut']
        date_fin = row_data['date_fin']
        heure_fin = row_data['heure_fin']

        datetime_debut = datetime.datetime(
            date_debut.year, date_debut.month,
            date_debut.day, heure_debut.hour)
        datetime_fin = datetime.datetime(
            date_fin.year, date_fin.month,
            date_fin.day, heure_fin.hour)
        if datetime_fin > datetime.datetime.now():
            datetime_fin = None

        obs_well_uuid = obs_wells[
            obs_wells['obs_well_id'] == row_data['no_piezometre']].index[0]

        repere = Repere(
            repere_uuid=uuid.uuid4(),
            sampling_feature_uuid=obs_well_uuid,
            top_casing_alt=row_data['alt_hors_sol'],
            casing_length=row_data['longueur_hors_sol'],
            start_date=datetime_debut,
            end_date=datetime_fin,
            is_alt_geodesic=row_data['elevation_geodesique'],
            )
        accessor._session.add(repere)
    accessor._session.commit()


def update_manual_measurements(filename, accessor):
    """
    Update the manual measurements in the database from an Excel file.
    """
    manual_measurements = accessor.get('manual_measurements')
    obs_wells = accessor.get('observation_wells_data')

    # Delete all observations related to water level manual measurements.
    for index in manual_measurements.index:
        accessor._del_manual_measurements(index)

    # Load the updated data.
    meas_data = pd.read_excel(filename)
    for row in range(len(meas_data)):
        row_data = meas_data.iloc[row]

        meas_date = row_data['date']
        meas_time = row_data['heure']
        meas_date_time = datetime.datetime(
            meas_date.year, meas_date.month, meas_date.day,
            meas_time.hour, meas_time.minute)

        try:
            obs_well_uuid = obs_wells[
                obs_wells['obs_well_id'] == row_data['no_piezometre']].index[0]
        except IndexError:
            # This means that the observation well does not exist in the DB,
            # so we skip it.
            continue

        attribute_values = {
            'value': row_data['lecture_profondeur'],
            'sampling_feature_uuid': obs_well_uuid,
            'datetime': meas_date_time
            }
        gen_num_value_id = accessor._create_index('manual_measurements')
        accessor.add_manual_measurements(gen_num_value_id, attribute_values)


def update_sondes_data(filename, accessor):
    """
    Update the sondes data in the database from an Excel file.
    """
    sondes_data = accessor.get('sondes_data')
    sonde_models_lib = accessor.get('sonde_models_lib')
    xls_sondes_data = pd.read_excel(filename)

    for i in range(len(xls_sondes_data)):
        row_data = xls_sondes_data.iloc[i]

        # Retrieve sonde data from the xls file.
        sonde_attributes = {
            'sonde_serial_no': row_data['No_Sonde'],
            'date_reception': (
                None if pd.isnull(row_data['Date-Réception']) else
                row_data['Date-Réception']),
            'date_withdrawal': (
                None if pd.isnull(row_data['Date_retrait']) else
                row_data['Date_retrait']),
            'in_repair': row_data['En_Réparation'],
            'out_of_order': row_data['Hors-service'],
            'lost': row_data['Perdue'],
            'off_network': row_data['Hors réseau'],
            'sonde_notes': (
                None if pd.isnull(row_data['Remarque']) else
                row_data['Remarque']),
            }

        try:
            model = row_data['Modèle'].replace(',', '.')
            company = row_data['Compagnie'].replace(',', '.')
            sonde_attributes['sonde_model_id'] = (sonde_models_lib[
                sonde_models_lib['sonde_brand_model'] == company + ' ' + model]
                .index[0])
        except AttributeError:
            continue

        # Update or load new sonde data in the database.
        try:
            sonde_uuid = (sondes_data[
                sondes_data['sonde_serial_no'] == row_data['No_Sonde']]
                .index[0])
            sonde = accessor._get_sonde(sonde_uuid)
            for name, value in sonde_attributes.items():
                setattr(sonde, name, value)
            accessor._session.commit()
            print('Updating sonde ', sonde_attributes['sonde_serial_no'],
                  model, company)
        except IndexError:
            sonde_uuid = accessor._create_index('sondes_data')
            accessor.add_sondes_data(sonde_uuid, sonde_attributes)
            print('Adding sonde ', sonde_attributes['sonde_serial_no'],
                  model, company)


def update_sonde_installations(filename, accessor):
    """
    Update the sonde installations in the database from an Excel file.
    """
    obs_wells = accessor.get('observation_wells_data')
    sonde_installs = accessor.get('sonde_installations')

    xls_installations = pd.read_excel(filename)
    for row in range(len(xls_installations)):
        row_data = xls_installations.iloc[row]
        date_debut = row_data['Date_debut']
        heure_debut = row_data['Heure_debut']
        date_fin = row_data['Date_fin']
        heure_fin = row_data['Heure_fin']

        datetime_debut = datetime.datetime(
            date_debut.year, date_debut.month,
            date_debut.day, heure_debut.hour, heure_debut.minute)
        try:
            datetime_fin = datetime.datetime(
                date_fin.year, date_fin.month,
                date_fin.day, heure_fin.hour, heure_fin.minute)
        except AttributeError:
            datetime_fin = None

        obs_well_uuid = obs_wells[
            obs_wells['obs_well_id'] == row_data['No_piezometre']].index[0]

        sonde_uuid = (sondes_data[
            sondes_data['sonde_serial_no'] == row_data['No_sonde']]
            .index[0])

        install_attributes = {
            'sonde_uuid': sonde_uuid,
            'start_date': datetime_debut,
            'end_date': datetime_fin,
            'install_depth': row_data['Profondeur'],
            'sampling_feature_uuid': obs_well_uuid,
            }

        # Update or load new sonde installation in the database.
        installs = (sonde_installs[
            sonde_installs['sonde_uuid'] == sonde_uuid])
        try:
            install_uuid = (installs[
                installs['start_date'] == datetime_debut].index[0])
        except IndexError:
            install_uuid = accessor._create_index('sonde_installations')
            accessor.add_sonde_installations(install_uuid, install_attributes)
        else:
            for name, value in install_attributes.items():
                accessor.set_sonde_installations(install_uuid, name, value,
                                                 auto_commit=False)
                accessor._session.commit()


if __name__ == "__main__":
    from sardes.config.database import get_dbconfig
    from time import perf_counter

    dbconfig = get_dbconfig('rsesq_postgresql')
    accessor = DatabaseAccessorRSESQ(**dbconfig)
    accessor.connect()

    obs_wells = accessor.get('observation_wells_data')
    obs_wells_stats = accessor.get_observation_wells_statistics()
    sondes_data = accessor.get('sondes_data')
    sonde_models_lib = accessor.get('sonde_models_lib')
    manual_measurements = accessor.get('manual_measurements')
    sonde_installations = accessor.get('sonde_installations')
    repere_data = accessor.get('repere_data')

    t1 = perf_counter()
    print('Fetching timeseries... ', end='')
    sampling_feature_uuid = accessor._get_obs_well_sampling_feature_uuid(
        '02340006')
    wlevel_data = accessor.get_timeseries_for_obs_well(
        sampling_feature_uuid, 0)
    print('done in {:0.3f} seconds'.format(perf_counter() - t1))

    accessor.close_connection()
