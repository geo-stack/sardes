# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

from __future__ import annotations

# ---- Standard imports
import datetime
import os
import os.path as osp
from typing import Any, Callable
import urllib

# ---- Third party imports
import numpy as np
import pandas as pd
from pandas import DataFrame
from qtpy.QtCore import Signal
import simplekml

# ---- Local imports
from sardes.api.database_model import DATABASE_CONCEPTUAL_MODEL
from sardes.api.timeseries import DataType
from sardes.api.taskmanagers import WorkerBase, TaskManagerBase
from sardes.config.locale import _
from sardes.config.ospath import get_documents_logo_filename
from sardes.config.main import CONF
from sardes.database.accessors.accessor_helpers import create_empty_readings
from sardes.tools.hydrographs import HydrographCanvas
from sardes.tools.save2excel import _save_reading_data_to_xlsx
from sardes.tools.waterquality import _save_hg_data_to_xlsx
from sardes.utils.data_operations import format_reading_data


class DatabaseConnectionWorker(WorkerBase):
    """
    A simple worker to create a new database session without blocking the gui.
    """
    sig_publish_progress = Signal(float)

    def __init__(self):
        super().__init__()
        self.db_accessor = None

        # Setup a cache structure for the tables and libraries.
        self._cache = {}
        self._stop_kml_publishing = False

    def clear_cache(self):
        """
        Clear the cache for the tables and libraries data.
        """
        print("Cleared the database worker cache.")
        self._cache = {}

    # ---- Worker connection state
    def is_connected(self):
        """Return whether a connection to a database is currently active."""
        return self.db_accessor is not None and self.db_accessor.is_connected()

    # ---- Task definition
    def _update_database(self, db_accessor):
        """Try to update the database schema to the latest version."""
        cur_version = db_accessor.version()
        req_version = db_accessor.req_version()
        print("Updating database from version {} to {}...".format(
            cur_version, req_version))

        from_version, to_version, error = db_accessor.update_database()
        return from_version, to_version, error

    def _connect_to_db(self, db_accessor):
        """Try to create a new connection with the database"""
        self.db_accessor = db_accessor
        print("Connecting to database with {}...".format(
            type(self.db_accessor).__name__))
        self.clear_cache()
        self.db_accessor.connect()
        if self.db_accessor._connection_error is None:
            print("Connection to database succeeded.")
        else:
            print("Connection to database failed.")
        return self.db_accessor._connection, self.db_accessor._connection_error

    def _disconnect_from_db(self):
        """Close the connection with the database"""
        print("Closing connection with database...")
        self.clear_cache()
        if self.db_accessor is not None:
            self.db_accessor.close_connection()
        print("Connection with database closed.")
        return None,

    # ---- Basic database operations
    def _add(self, name: str, values: list[dict],
             indexes: list[Any] = None, auto_commit: bool = True):
        """
        Add a new item to the data related to name in the database.
        """
        if name in self._cache:
            del self._cache[name]
        self.db_accessor.add(name, values, indexes, auto_commit)

    def _get(self, name, *args, **kargs):
        """
        Get the data related to name from the database.
        """
        if name in self._cache:
            print("Fetching '{}' from store.".format(name))
            return self._cache[name],

        print("Fetching '{}' from the database...".format(name))
        if self.is_connected():
            try:
                data = self.db_accessor.get(name)
                data.attrs['name'] = name
                print("Successfully fetched '{}' from the database."
                      .format(name))
            except Exception as e:
                print(("Failed to fetch '{}' from the database "
                       "because of the following error."
                       ).format(name))
                print(e)
                print('-' * 20)
                data = DataFrame([])
                data.attrs['name'] = name
            else:
                self._cache[name] = data
        else:
            print(("Failed to fetch '{}' from the database "
                   "because Sardes is not connected to a database."
                   ).format(name))
            data = DataFrame([])
            data.attrs['name'] = name

        return data,

    def _delete(self, name: str, indexes: list[Any], auto_commit: bool = True):
        """
        Delete from the database the items related to name at the
        specified indexes.
        """
        if name in self._cache:
            del self._cache[name]
        self.db_accessor.delete(name, indexes, auto_commit)

    def _set(self, name: str, index: Any,
             values: dict, auto_commit: bool = True):
        """
        Save the data related to name in the database.
        """
        if name in self._cache:
            del self._cache[name]
        self.db_accessor.set(name, index, values, auto_commit)

    def _save_table_edits(self, name, deleted_rows, added_rows, edited_values):
        """
        Save the changes made to table 'name' to the database.
        """
        print("Saving edits for table '{}' in the database...".format(name))

        # We delete rows from the database.
        if not deleted_rows.empty:
            self._delete(name, deleted_rows, auto_commit=False)

        # We add new rows to the database.
        if not added_rows.empty:
            values = [row.dropna().to_dict() for
                      idx, row in added_rows.iterrows()]
            self._add(name, values, auto_commit=False)

        # We commit edits to existing rows.
        for index, values in edited_values.groupby(level=0):
            values.index = values.index.droplevel(0)
            self._set(name,
                      index,
                      values['edited_value'].to_dict(),
                      auto_commit=False)

        self.db_accessor.commit_transaction()

        print("Edits for table '{}' saved successfully in the database..."
              .format(name))

        # Get and return the updated table.
        return self._get(name)[0],

    def _check_foreign_constraints(self, parent_indexes, data_name):
        """
        Return the first foreign constraint violation found by checking
        the parent indexes of the data related to data_name against the
        foreign constraints specified in FOREIGN_CONSTRAINTS.
        """
        foreign_constraints = (
            DATABASE_CONCEPTUAL_MODEL[data_name].foreign_constraints)
        for foreign_constraint in foreign_constraints:
            foreign_table = foreign_constraint.foreign_table
            foreign_column = foreign_constraint.foreign_column
            foreign_data = self._get(foreign_table)[0]

            isin_indexes = parent_indexes[
                parent_indexes.isin(foreign_data[foreign_column].array)]
            if not isin_indexes.empty:
                return (isin_indexes[0], foreign_column, foreign_table),
        else:
            return None,

    # ---- Timeseries
    def _save_readings_edits(self, station_id, tseries_edits, tseries_dels):
        """
        Save the changes made to readings data related to the specified
        station id.
        """
        self._save_timeseries_data_edits(tseries_edits, auto_commit=False)
        self._delete_timeseries_data(tseries_dels, auto_commit=False)
        self.db_accessor.commit_transaction()
        return self._get_timeseries_for_obs_well(station_id)[0],

    def _get_timeseries_for_obs_well(self, sampling_feature_uuid,
                                     data_types=None):
        """
        Return a pandas dataframe containing the readings for the given
        data types and monitoring station.

        If no data type are specified, then return the entire dataset for
        the specified monitoring station.
        """
        # We do this like this to avoid unecessary prints in the console.
        if 'observation_wells_data' in self._cache:
            obs_well_data = self._cache['observation_wells_data']
        else:
            obs_well_data = self._get('observation_wells_data')[0]
        obs_well_data = obs_well_data.loc[sampling_feature_uuid]

        if data_types is None:
            data_types = [
                DataType.WaterLevel,
                DataType.WaterTemp,
                DataType.WaterEC]

        obs_well_id = obs_well_data['obs_well_id']
        print("Fetching readings data for observation well {}..."
              .format(obs_well_id))
        try:
            readings = self.db_accessor.get_timeseries_for_obs_well(
                sampling_feature_uuid, data_types)
        except Exception as error:
            print(("Failed to fetch readings data for observation well {} "
                   "because of the following error:").format(obs_well_id))
            print(type(error).__name__, end=': ')
            print(error)
            readings = create_empty_readings(data_types)
        else:
            print("Successfully fetched readings data for observation well {}."
                  .format(obs_well_id))

        # Add metadata to the dataframe.
        readings._metadata = ['sampling_feature_data']
        readings.sampling_feature_data = obs_well_data

        # Check for duplicates along the time axis.
        duplicated = readings.duplicated(subset=['datetime', 'sonde_id'])
        nbr_duplicated = np.sum(duplicated)
        if nbr_duplicated:
            print(("Warning: {} duplicated entrie(s) were found while "
                   "fetching readings data for well {}."
                   ).format(nbr_duplicated, obs_well_data['obs_well_id']))

        return readings,

    def _save_timeseries_data_edits(self, tseries_edits, auto_commit=True):
        """
        Save in the database a set of edits that were made to to timeseries
        data that were already saved in the database.
        """
        print("Saving timeseries data edits...")
        if 'observation_wells_data_overview' in self._cache:
            del self._cache['observation_wells_data_overview']
        self.db_accessor.save_timeseries_data_edits(tseries_edits, auto_commit)
        print("Timeseries data edits saved sucessfully.")

    def _add_timeseries_data(self, tseries_data, obs_well_uuid,
                             sonde_installation_uuid, auto_commit=True):
        """
        Save in the database a set of timeseries data associated with the
        given well and sonde installation id.
        """
        print("Adding timeseries data...")
        if 'observation_wells_data_overview' in self._cache:
            del self._cache['observation_wells_data_overview']
        self.db_accessor.add_timeseries_data(
            tseries_data, obs_well_uuid, sonde_installation_uuid, auto_commit)
        print("Timeseries data added sucessfully.")

    def _delete_timeseries_data(self, tseries_dels, auto_commit=True):
        """
        Delete data in the database for the observation IDs, datetime and
        data type specified in tseries_dels.
        """
        print("Deleting timeseries data...")
        if 'observation_wells_data_overview' in self._cache:
            del self._cache['observation_wells_data_overview']
        self.db_accessor.delete_timeseries_data(tseries_dels, auto_commit)
        print("Timeseries data deleted sucessfully.")

    # ---- Attachments
    def _get_attachment(self, sampling_feature_uuid, attachment_type):
        """
        Return the data and filename of the attachment of the given type that
        is attached to the specified sampling_feature_uuid.
        """
        return self.db_accessor.get_attachment(
            sampling_feature_uuid, attachment_type)

    def _set_attachment(self, sampling_feature_uuid, attachment_type,
                        filename):
        """
        Save and attach the given attachment to the specified
        sampling_feature_uuid in the database.
        """
        if 'attachments_info' in self._cache:
            del self._cache['attachments_info']
        self.db_accessor.set_attachment(
            sampling_feature_uuid, attachment_type, filename)

    def _del_attachment(self, sampling_feature_uuid, attachment_type):
        """
        Delete from the database the attachment of the specified type that
        is currently attached to the specified sampling_feature_uuid.
        """
        if 'attachments_info' in self._cache:
            del self._cache['attachments_info']
        self.db_accessor.del_attachment(
            sampling_feature_uuid, attachment_type)

    # ---- Utilities
    def _get_water_quality_data(self, station_id):
        """
        Return the formatted hydrogeochemical data for the specified
        monitoring station ID.
        """
        water_quality_data = pd.DataFrame()
        water_quality_data.attrs['station_id'] = station_id
        if not self.is_connected():
            return water_quality_data,

        hg_surveys = self._get('hg_surveys')[0]
        hg_params = self._get('hg_params')[0]
        measurement_units = self._get('measurement_units')[0]
        hg_param_values = self._get('hg_param_values')[0]

        station_data = self._get('observation_wells_data')[0].loc[station_id]
        sta_hg_surveys = hg_surveys[
            hg_surveys['sampling_feature_uuid'] == station_id
            ]
        if sta_hg_surveys.empty:
            return water_quality_data,

        repere_data = self._get('repere_data')[0]
        station_repere_data = (
            repere_data
            [repere_data['sampling_feature_uuid'] == station_id]
            .copy())

        for hg_survey_id, hg_survey_data in sta_hg_surveys.iterrows():
            hg_survey_date = hg_survey_data['hg_survey_datetime']

            _to_merge = hg_param_values.loc[
                hg_param_values['hg_survey_id'] == hg_survey_id
                ]
            if _to_merge.empty:
                continue

            _to_merge = _to_merge[
                ['hg_param_id', 'hg_param_value', 'meas_units_id']
                ].copy()
            _to_merge['hg_param_id'] = (
                _to_merge['hg_param_id']
                .map(hg_params['hg_param_name'].to_dict().get)
                )
            _to_merge['meas_units_id'] = (
                _to_merge['meas_units_id']
                .map(measurement_units['meas_units_abb'].to_dict().get)
                )
            _to_merge = _to_merge.set_index('hg_param_id')
            _to_merge.columns = pd.MultiIndex.from_tuples(
                [(hg_survey_date, col) for col in _to_merge.columns]
                )

            if water_quality_data.empty:
                water_quality_data = _to_merge
            else:
                water_quality_data = water_quality_data.merge(
                    _to_merge, how='outer', left_index=True, right_index=True)
        water_quality_data.attrs['station_data'] = station_data
        water_quality_data.attrs['station_repere_data'] = station_repere_data

        return water_quality_data,

    def _get_sonde_installation_info(self, sonde_serial_no, date_time):
        """
        Fetch and return from the database the installation infos related to
        the given sonde serial number and datetime.
        """
        if not self.is_connected():
            return None,

        sonde_data = self._get('sondes_data')[0]
        try:
            sonde_uuid = (
                sonde_data[sonde_data['sonde_serial_no'] == sonde_serial_no]
                .index[0])
        except (KeyError, IndexError):
            return None,

        sonde_installations = self._get('sonde_installations')[0]
        try:
            installs = (
                sonde_installations
                [sonde_installations['sonde_uuid'] == sonde_uuid]
                )
        except (KeyError, IndexError):
            return None,
        else:
            for i in range(len(installs)):
                sonde_install = installs.iloc[i].copy()
                start_date = sonde_install['start_date']
                end_date = (sonde_install['end_date'] if
                            not pd.isnull(sonde_install['end_date']) else
                            datetime.datetime.now())
                if start_date <= date_time and end_date >= date_time:
                    break
            else:
                return None,

        # Add information about well name and municipality.
        obs_wells_data = self._get('observation_wells_data')[0]
        obs_well_uuid = sonde_install['sampling_feature_uuid']
        sonde_install['well_name'] = obs_wells_data.at[
            obs_well_uuid, 'obs_well_id']
        sonde_install['well_common_name'] = obs_wells_data.at[
            obs_well_uuid, 'common_name']
        sonde_install['well_municipality'] = obs_wells_data.at[
            obs_well_uuid, 'municipality']

        # Add sonde brand and model info.
        sonde_model_id = sonde_data.loc[sonde_uuid]['sonde_model_id']
        sonde_models_lib = self._get('sonde_models_lib')[0]
        sonde_install['sonde_brand_model'] = sonde_models_lib.loc[
            sonde_model_id, 'sonde_brand_model']

        return sonde_install,

    # ---- Publish Network Data
    def _publish_to_kml(self, kml_filename, iri_data=None, iri_logs=None,
                        iri_graphs=None, iri_quality=None):
        """
        Publish the piezometric network data to the specified kml filename.

        Parameters
        ----------
        kml_filename : str
            The absolute path where to save the kml file.
        iri_data : str, optional
            The IRI where the readings data files are going to be hosted.
            The default is None.
        iri_logs : str, optional
            The IRI where the construction logs are going to be hosted.
            The default is None.
        iri_graphs : str, optional
            The IRI where the hydrographs are going to be hosted.
            The default is None.
        iri_quality : str, optional
            The IRI where the water quality reports are going
            to be hosted. The default is None.

        Returns
        -------
        results : bool
            Whether the publishing of the piezometric network was successful.
        """
        self._stop_kml_publishing = False

        # Create the files and folder architecture.
        files_dirname = osp.join(
            osp.dirname(kml_filename),
            osp.splitext(osp.basename(kml_filename))[0] + '_files'
            )
        data_dirname = osp.join(files_dirname, 'data')
        if not osp.exists(data_dirname):
            os.makedirs(data_dirname)
        logs_dirname = osp.join(files_dirname, 'diagrams')
        if not osp.exists(logs_dirname):
            os.makedirs(logs_dirname)
        graphs_dirname = osp.join(files_dirname, 'graphs')
        if not osp.exists(graphs_dirname):
            os.makedirs(graphs_dirname)
        quality_dirname = osp.join(files_dirname, 'quality')
        if not osp.exists(quality_dirname):
            os.makedirs(quality_dirname)

        # Initialize a new KML document.
        kml = simplekml.Kml()
        fol = simplekml.Folder()
        kml.document = fol

        # Define the style for the placemarks.
        pnt_style = simplekml.Style()
        pnt_style.iconstyle.icon.href = (
            'http://maps.google.com/mapfiles/kml/paddle/blu-circle.png')
        pnt_style.iconstyle.scale = 0.8
        pnt_style.labelstyle.color = 'bfffffff'
        pnt_style.labelstyle.scale = 0.8

        repere_data, = self._get('repere_data')
        stations_data_overview, = self._get('observation_wells_data_overview')
        stations_data, = self._get('observation_wells_data')
        stations_data['locations'] = list(zip(
            stations_data['longitude'].astype(float).round(decimals=4),
            stations_data['latitude'].astype(float).round(decimals=4)
            ))
        unique_locations = (
            stations_data[['locations']]
            .drop_duplicates(['locations'])
            .values.flatten().tolist()
            )

        progress = 0
        progress_total = len(stations_data)
        for loc in unique_locations:
            if self._stop_kml_publishing:
                return False,

            pnt = fol.newpoint(coords=[loc])
            pnt.style = pnt_style

            loc_stations_data = (
                stations_data[stations_data['locations'] == loc]
                .sort_values(['obs_well_id'], ascending=True))

            municipality = loc_stations_data['municipality'].values[0]
            pnt.name = municipality

            pnt_desc = '<![CDATA['
            for station_uuid, station_data in loc_stations_data.iterrows():
                progress += 1
                station_data = stations_data.loc[station_uuid]
                is_station_active = station_data['is_station_active']
                station_repere_data = (
                    repere_data
                    [repere_data['sampling_feature_uuid'] == station_uuid]
                    .copy())
                if not station_repere_data.empty:
                    station_repere_data = (
                        station_repere_data
                        .sort_values(by=['end_date'], ascending=[True]))
                else:
                    station_repere_data = pd.Series([], dtype=object)
                last_repere_data = station_repere_data.iloc[-1]
                ground_altitude = (
                    last_repere_data['top_casing_alt'] -
                    last_repere_data['casing_length'])
                is_alt_geodesic = last_repere_data['is_alt_geodesic']

                pnt_desc += '{} = {}<br/>'.format(
                    _('Station'),
                    station_data['obs_well_id'])
                pnt_desc += '{} = {:0.4f}<br/>'.format(
                    _('Longitude'),
                    station_data['longitude'])
                pnt_desc += '{} = {:0.4f}<br/>'.format(
                    _('Latitude'),
                    station_data['latitude'])
                pnt_desc += '{} = {:0.2f} {} ({})<br/>'.format(
                    _('Ground Alt.'),
                    ground_altitude,
                    _('m MSL'),
                    _('Geodesic') if is_alt_geodesic else _('Approximate'))
                pnt_desc += '{} = {}<br/>'.format(
                    _('Water-table'),
                    station_data['confinement'])
                pnt_desc += '{} = {}<br/>'.format(
                    _('Influenced'),
                    station_data['is_influenced'])
                pnt_desc += '<br/>'
                if station_uuid in stations_data_overview.index:
                    last_reading = (stations_data_overview
                                    .loc[station_uuid]['last_date'])
                    pnt_desc += '{} = {}<br/>'.format(
                        _('Last reading'),
                        last_reading.strftime('%Y-%m-%d'))
                pnt_desc += '{} = {}<br/>'.format(
                    _('Status'),
                    _('Active') if is_station_active else _('Inactive'))

                # Fetch data from the database.
                if iri_data is not None or iri_graphs is not None:
                    readings, = self._get_timeseries_for_obs_well(
                        station_uuid,
                        data_types=[DataType.WaterLevel,
                                    DataType.WaterTemp,
                                    DataType.WaterEC])
                    formatted_data = format_reading_data(
                        readings, station_repere_data)
                if iri_logs is not None:
                    log_data, log_fame = (
                        self.db_accessor.get_attachment(station_uuid, 1))
                if iri_quality is not None:
                    quality_data, = self._get_water_quality_data(station_uuid)

                # Generate the attached files and add the urls.
                files_urls = ''
                if iri_data is not None and not readings.empty:
                    xlsx_filename = _('readings_{}.xlsx').format(
                        station_data['obs_well_id'])
                    xlsx_savepath = osp.join(data_dirname, xlsx_filename)
                    try:
                        _save_reading_data_to_xlsx(
                            xlsx_savepath,
                            _('Piezometry'),
                            formatted_data,
                            station_data,
                            ground_altitude,
                            is_alt_geodesic,
                            logo_filename=get_documents_logo_filename(),
                            font_name=CONF.get(
                                'documents_settings', 'xlsx_font')
                            )
                    except PermissionError as e:
                        print(e)

                    url = urllib.parse.quote(
                        iri_data + '/' + xlsx_filename, safe='/:')
                    files_urls += '<a href="{}">{}</a><br/>'.format(
                        url, _("Data"))  # Données
                if iri_logs is not None and log_data is not None:
                    root, ext = osp.splitext(log_fame)
                    log_filename = _('diagram_{}{}').format(
                        station_data['obs_well_id'], ext)
                    log_savepath = osp.join(logs_dirname, log_filename)
                    try:
                        with open(log_savepath, 'wb') as f:
                            f.write(log_data)
                    except PermissionError as e:
                        print(e)

                    url = urllib.parse.quote(
                        iri_logs + '/' + log_filename, safe='/:')
                    files_urls += '<a href="{}">{}</a><br/>'.format(
                        url, _("Diagram"))
                if iri_graphs is not None and not readings.empty:
                    graph_filename = _('graph_{}.pdf').format(
                        station_data['obs_well_id'])
                    graph_savepath = osp.join(graphs_dirname, graph_filename)
                    hydrograph = HydrographCanvas(
                        formatted_data,
                        station_data,
                        ground_altitude,
                        is_alt_geodesic,
                        fontname=CONF.get('documents_settings', 'graph_font')
                        )
                    try:
                        hydrograph.figure.savefig(graph_savepath, dpi=300)
                    except PermissionError as e:
                        print(e)

                    url = urllib.parse.quote(
                        iri_graphs + '/' + graph_filename, safe='/:')
                    files_urls += '<a href="{}">{}</a><br/>'.format(
                        url, _("Graph"))
                if iri_quality is not None and not quality_data.empty:
                    quality_filename = _(
                        "water_quality_{}.xlsx"
                        ).format(station_data['obs_well_id'])
                    quality_savepath = osp.join(
                        quality_dirname, quality_filename)
                    try:
                        _save_hg_data_to_xlsx(
                            quality_savepath,
                            _('Water Quality'),
                            quality_data,
                            quality_data.attrs['station_data'],
                            ground_altitude,
                            is_alt_geodesic,
                            logo_filename=get_documents_logo_filename(),
                            font_name=CONF.get(
                                'documents_settings', 'xlsx_font')
                            )
                    except PermissionError as e:
                        print(e)

                    url = urllib.parse.quote(
                        iri_quality + '/' + quality_filename, safe='/:')
                    files_urls += '<a href="{}">{}</a><br/>'.format(
                        url, _("Water Quality"))
                if files_urls:
                    pnt_desc += '<br/>' + files_urls

                if station_uuid != loc_stations_data.index[-1]:
                    pnt_desc += '--<br/>'
                self.sig_publish_progress.emit(progress / progress_total * 100)
            pnt_desc += '<br/>]]>'
            pnt.description = pnt_desc
        kml.save(kml_filename)
        return True,


class DatabaseConnectionManager(TaskManagerBase):
    sig_database_connected = Signal(object, object)
    sig_database_disconnected = Signal()
    sig_database_is_connecting = Signal()
    sig_database_connection_changed = Signal(bool)
    sig_database_is_updating = Signal()
    sig_database_updated = Signal(int, int, object)

    sig_database_data_changed = Signal(list)
    sig_tseries_data_changed = Signal(list)
    sig_publish_progress = Signal(float)

    def __init__(self):
        super().__init__()
        self._is_connecting = False
        self._is_updating = False
        self._data_changed = set()
        self._tseries_data_changed = set()
        self._confirm_before_saving_edits = True

        self.set_worker(DatabaseConnectionWorker())
        self.sig_run_tasks_finished.connect(self._handle_run_tasks_finished)
        self.worker().sig_publish_progress.connect(
            self.sig_publish_progress.emit)

    def is_connected(self):
        """Return whether a connection to a database is currently active."""
        return self.worker().is_connected()

    def is_connecting(self):
        """
        Return whether a connection to a database is currently being created.
        """
        return self._is_connecting

    def is_updating(self):
        """
        Return whether the database is being updated.
        """
        return self._is_updating

    def confirm_before_saving_edits(self):
        """
        Return wheter we should ask confirmation to the user before saving
        data edits to the database.
        """
        return self._confirm_before_saving_edits

    def set_confirm_before_saving_edits(self, x):
        """
        Set wheter we should ask confirmation to the user before saving
        data edits to the database.
        """
        self._confirm_before_saving_edits = bool(x)

    # ---- Public methods
    def add(self, *args, callback=None, postpone_exec=False):
        """
        Add a new item to the data related to name in the database.
        """
        self._data_changed.add(args[0])
        self.add_task('add', callback, *args)
        if not postpone_exec:
            self.run_tasks()

    def get(self, *args, callback=None, postpone_exec=False):
        """
        Get the data related to name from the database.
        """
        self.add_task('get', callback, *args)
        if not postpone_exec:
            self.run_tasks()

    def delete(self, name: str, indexes: list, callback: Callable = None,
               postpone_exec: bool = False):
        """
        Delete an item related to name from the database.
        """
        self._data_changed.add(name)
        self.add_task('delete', callback, name, indexes)
        if not postpone_exec:
            self.run_tasks()

    def set(self, *args, callback=None, postpone_exec=False):
        """
        Set the data related to name in the database.
        """
        self._data_changed.add(args[0])
        self.add_task('set', callback, *args)
        if not postpone_exec:
            self.run_tasks()

    def connect_to_db(self, db_accessor):
        """
        Try to create a new connection with the database using the
        provided database accessor.
        """
        if db_accessor is None:
            return
        self._is_connecting = True
        self.sig_database_is_connecting.emit()
        self.add_task(
            'connect_to_db', self._handle_connect_to_db, db_accessor)
        self.run_tasks()

    def disconnect_from_db(self):
        """Close the connection with the database"""
        self.add_task('disconnect_from_db', self._handle_disconnect_from_db)
        self.run_tasks()

    def close(self, callback=None):
        """Close the database connection manager."""
        self.add_task('disconnect_from_db', callback)
        self.run_tasks()

    def update_database(self, db_accessor):
        self._is_updating = True
        self.sig_database_is_updating.emit()
        self._add_task(
            'update_database',
            lambda *args: self._handle_database_updated(*args),
            db_accessor)
        self.run_tasks()

    # ---- Utilities
    def get_water_quality_data(self, station_id, callback=None,
                               postpone_exec=False):
        """
        Fetch and return from the database the water quality data
        related to the given monitoring station.
        """
        self.add_task('get_water_quality_data', callback, station_id)
        if not postpone_exec:
            self.run_tasks()

    def get_sonde_installation_info(self, sonde_serial_no, date_time,
                                    callback=None, postpone_exec=False):
        """
        Fetch and return from the database the installation infos related to
        the given sonde serial number and datetime.
        """
        self.add_task('get_sonde_installation_info', callback,
                      sonde_serial_no, date_time)
        if not postpone_exec:
            self.run_tasks()

    # ---- Timeseries
    def get_timeseries_for_obs_well(
            self, obs_well_id, data_types=None,
            callback=None, postpone_exec=False, main_thread=False):
        """
        Return a pandas dataframe containing the readings for the given
        data types and monitoring station.

        If no data type are specified, then return the entire dataset for
        the specified monitoring station.
        """
        if main_thread is False:
            self.add_task('get_timeseries_for_obs_well', callback,
                          obs_well_id, data_types)
            if not postpone_exec:
                self.run_tasks()
        else:
            tseries_groups = (
                self.worker()._get_timeseries_for_obs_well(
                    obs_well_id, data_types)
                )[0]
            if callback is not None:
                callback(tseries_groups)
            return tseries_groups

    def save_timeseries_data_edits(self, tseries_edits, obs_well_id,
                                   callback=None, postpone_exec=False):
        """
        Save in the database a set of edits that were made to timeseries
        data that were already saved in the database.

        Parameters
        ----------
        tseries_edits: pandas.DataFrame
            A multi-indexes pandas dataframe that contains the edited
            numerical values that need to be saved in the database.
            The indexes of the dataframe correspond, respectively, to the
            datetime (datetime), observation ID (str) and the data type
            (DataType) corresponding to the edited value.
        obs_well_id: object
            A unique identifier used to reference the observation well in
            the database for which time series data will be edited.
        """
        self._data_changed.add('observation_wells_data_overview')
        self._tseries_data_changed.add(obs_well_id)
        self.add_task('save_timeseries_data_edits', callback, tseries_edits)
        if not postpone_exec:
            self.run_tasks()

    def add_timeseries_data(self, tseries_data, obs_well_id,
                            sonde_installation_uuid=None, callback=None,
                            postpone_exec=False):
        """
        Save in the database a set of timeseries data associated with the
        given well and sonde installation id.

        Parameters
        ----------
        tseries_data: pandas.DataFrame
            A pandas dataframe where time is saved as datetime in a column
            named 'datetime'. The columns in which the numerical values are
            saved must be a member of :class:`sardes.api.timeseries.DataType`
            enum.
        obs_well_id: object
            A unique identifier used to reference the observation well in
            the database for which time series data will be added.
        """
        self._data_changed.add('observation_wells_data_overview')
        self._tseries_data_changed.add(obs_well_id)
        self.add_task('add_timeseries_data', callback, tseries_data,
                      obs_well_id, sonde_installation_uuid)
        if not postpone_exec:
            self.run_tasks()

    def delete_timeseries_data(self, tseries_dels, obs_well_id, callback=None,
                               postpone_exec=False):
        """
        Delete data in the database for the observation IDs, datetime and
        data type specified in tseries_dels.

        Parameters
        ----------
        tseries_dels: pandas.DataFrame
            A pandas dataframe that contains the observation IDs, datetime,
            and datatype for which timeseries data need to be deleted
            from the database.
        obs_well_id: object
            A unique identifier used to reference the observation well in
            the database for which time series data will be deleted.
        """
        self._data_changed.add('observation_wells_data_overview')
        self._tseries_data_changed.add(obs_well_id)
        self.add_task('delete_timeseries_data', callback, tseries_dels)
        if not postpone_exec:
            self.run_tasks()

    # ---- Attachments
    def get_attachment(self, sampling_feature_uuid, attachment_type,
                       callback=None, postpone_exec=False):
        """
        Return the data and filename of the attachment of the given type that
        is attached to the specified sampling_feature_uuid.
        """
        self.add_task('get_attachment', callback,
                      sampling_feature_uuid, attachment_type)
        if not postpone_exec:
            self.run_tasks()

    def set_attachment(self, sampling_feature_uuid, attachment_type,
                       filename, callback=None, postpone_exec=False):
        """
        Save and attach the given attachment to the specified
        sampling_feature_uuid in the database.
        """
        self._data_changed.add('attachments_info')
        self.add_task('set_attachment', callback,
                      sampling_feature_uuid, attachment_type, filename)
        if not postpone_exec:
            self.run_tasks()

    def del_attachment(self, sampling_feature_uuid, attachment_type,
                       callback=None, postpone_exec=False):
        """
        Delete from the database the attachment of the specified type that
        is currently attached to the specified sampling_feature_uuid.
        """
        self._data_changed.add('attachments_info')
        self.add_task(
            'del_attachment', callback,
            sampling_feature_uuid, attachment_type)
        if not postpone_exec:
            self.run_tasks()

    # ---- Handlers
    def _handle_database_updated(self, from_version, to_version, error):
        """
        Handle when the database was updated successfully or not.
        """
        self._is_updating = False
        self.sig_database_updated.emit(from_version, to_version, error)

    def _handle_connect_to_db(self, connection, connection_error):
        """
        Handle when a connection to the database was created successfully
        or not.
        """
        self._is_connecting = False
        self.sig_database_connected.emit(connection, connection_error)
        self.sig_database_connection_changed.emit(self.is_connected())

    def _handle_disconnect_from_db(self, *args, **kargs):
        """
        Handle when the connection to the database was closed successfully.
        """
        self.sig_database_disconnected.emit()
        self.sig_database_connection_changed.emit(self.is_connected())

    def _handle_run_tasks_finished(self):
        """
        Handle when all tasks that needed to be run by the worker are
        completed.
        """
        if len(self._data_changed):
            self.sig_database_data_changed.emit(list(self._data_changed))
            self._data_changed = set()
        if len(self._tseries_data_changed):
            self.sig_tseries_data_changed.emit(
                list(self._tseries_data_changed))
            self._tseries_data_changed = set()

    # ---- Publish Network Data
    def publish_to_kml(self, filename, iri_data=None, iri_logs=None,
                       iri_graphs=None, iri_quality=None, callback=None,
                       postpone_exec=False):
        """
        Publish the piezometric network data to the specified kml filename.
        """
        self.add_task('publish_to_kml', callback, filename,
                      iri_data, iri_logs, iri_graphs, iri_quality)
        if not postpone_exec:
            self.run_tasks()


if __name__ == '__main__':
    from sardes.database.accessors import DatabaseAccessorSardesLite

    db_accessor = DatabaseAccessorSardesLite(
        'D:/Desktop/rsesq_prod_21072020_v1.db')
    dbmanager = DatabaseConnectionManager()
    dbmanager.connect_to_db(db_accessor)
    sampling_feature_uuid = (
        db_accessor._get_sampling_feature_uuid_from_name('01070001'))

    readings = dbmanager.get_timeseries_for_obs_well(
        sampling_feature_uuid,
        [DataType.WaterLevel, DataType.WaterTemp],
        callback=None,
        postpone_exec=False, main_thread=True)
    print(readings)

    dbmanager.close()
