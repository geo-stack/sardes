# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Third party imports
import pandas as pd
from qtpy.QtCore import Signal, QUrl
from qtpy.QtGui import QDesktopServices

# ---- Local imports
from sardes.api.tablemodels import SardesTableColumn
from sardes.config.gui import get_iconsize
from sardes.config.locale import _
from sardes.utils.qthelpers import create_toolbutton
from sardes.widgets.tableviews import SardesTableWidget
from sardes.tables.models import StandardSardesTableModel
from sardes.tables.managers import FileAttachmentManager
from sardes.tables.delegates import (
    StringEditDelegate, BoolEditDelegate,
    NumEditDelegate, NotEditableDelegate, TextEditDelegate)
from sardes.tables.errors import ForeignReadingsConstraintError


class ObsWellsTableModel(StandardSardesTableModel):
    """
    A table model to display the list of observation wells that are saved
    in the database.
    """
    __tablename__ = 'table_observation_wells'
    __tabletitle__ = _('Observation Wells')
    __tablecolumns__ = [
        SardesTableColumn(
            'obs_well_id', _('Well ID'), 'str', notnull=True, unique=True,
            delegate=StringEditDelegate),
        SardesTableColumn(
            'common_name', _('Common Name'), 'str',
            delegate=StringEditDelegate),
        SardesTableColumn(
            'municipality', _('Municipality'), 'str',
            delegate=StringEditDelegate),
        SardesTableColumn(
            'aquifer_type', _('Aquifer'), 'str',
            delegate=StringEditDelegate),
        SardesTableColumn(
            'aquifer_code', _('Aquifer Code'), 'Int64',
            delegate=NumEditDelegate,
            delegate_options={
                'decimals': 0, 'minimum': 0, 'maximum': 999}),
        SardesTableColumn(
            'confinement', _('Confinement'), 'str',
            delegate=StringEditDelegate),
        SardesTableColumn(
            'in_recharge_zone', _('Recharge Zone'), 'str',
            delegate=StringEditDelegate),
        SardesTableColumn(
            'is_influenced', _('Influenced'), 'str',
            delegate=StringEditDelegate),
        SardesTableColumn(
            'latitude', _('Latitude'), 'float64',
            delegate=NumEditDelegate,
            delegate_options={'decimals': 16, 'minimum': -180, 'maximum': 180},
            ),
        SardesTableColumn(
            'longitude', _('Longitude'), 'float64',
            delegate=NumEditDelegate,
            delegate_options={'decimals': 16, 'minimum': -180, 'maximum': 180},
            ),
        SardesTableColumn(
            'first_date', _('First Date'), 'datetime64[ns]',
            delegate=NotEditableDelegate, editable=False),
        SardesTableColumn(
            'last_date', _('Last Date'), 'datetime64[ns]',
            delegate=NotEditableDelegate, editable=False),
        SardesTableColumn(
            'mean_water_level', _('Mean level (m)'), 'float64',
            delegate=NotEditableDelegate, editable=False),
        SardesTableColumn(
            'is_station_active', _('Active'), 'boolean', notnull=True,
            delegate=BoolEditDelegate),
        SardesTableColumn(
            'obs_well_notes', _('Notes'), dtype='str',
            delegate=TextEditDelegate)
        ]

    __dataname__ = 'observation_wells_data'
    __libnames__ = ['observation_wells_data_overview',
                    'attachments_info']

    def _check_foreign_constraint(self, callback):
        """
        Extend base class method to check for Readings FOREIGN constraint.
        """
        deleted_rows = self._datat.deleted_rows()
        if not deleted_rows.empty:
            readings_overview = self.libraries[
                'observation_wells_data_overview']
            isin_indexes = deleted_rows[
                deleted_rows.isin(readings_overview.index)]
            if not isin_indexes.empty:
                callback(ForeignReadingsConstraintError(isin_indexes[0]))
                return
        super()._check_foreign_constraint(callback)

    def set_model_data(self, dataf, dataf_columns_mapper=None):
        """
        Extend SardesTableModelBase base class method to make sure we use
        a column dtype that is capable to handle integer nan values.

        See https://pandas.pydata.org/pandas-docs/stable/user_guide/
            gotchas.html#support-for-integer-na
        """
        if 'aquifer_code' not in dataf.columns:
            dataf['aquifer_code'] = None
        dataf['aquifer_code'] = dataf['aquifer_code'].astype(pd.Int64Dtype())
        return super().set_model_data(dataf, dataf_columns_mapper)

    # ---- Visual Data
    def logical_to_visual_data(self, visual_dataf):
        """
        Transform logical data to visual data.
        """
        try:
            obs_wells_stats = self.libraries['observation_wells_data_overview']
        except KeyError:
            pass
        else:
            for column in ['first_date', 'last_date', 'mean_water_level']:
                if column in obs_wells_stats.columns:
                    visual_dataf[column] = obs_wells_stats[column]
        visual_dataf['is_station_active'] = (
            visual_dataf['is_station_active']
            .map({True: _('Yes'), False: _('No')}.get)
            )
        return visual_dataf


class ObsWellsTableWidget(SardesTableWidget):
    sig_view_data = Signal(object, bool)

    def __init__(self, *args, **kargs):
        table_model = ObsWellsTableModel()
        super().__init__(table_model, *args, **kargs)

        self.add_toolbar_separator()
        for button in self._create_extra_toolbuttons():
            self.add_toolbar_widget(button)

    # ---- SardesPaneWidget public API
    def register_to_plugin(self, plugin):
        """Register this table with the given plugin."""
        self.sig_view_data.connect(plugin.main.view_timeseries_data)
        self.construction_logs_manager.set_dbmanager(
            plugin.main.db_connection_manager)
        self.water_quality_reports.set_dbmanager(
            plugin.main.db_connection_manager)

    # ---- SardesTableWidget public API
    def on_current_changed(self, current_index):
        """
        Implemement on_current_changed SardesTableWidget method.
        """
        if current_index.isValid():
            is_new_row = self.model().is_new_row_at(current_index)
            self.show_data_btn.setEnabled(not is_new_row)
            self.construction_logs_manager.setEnabled(not is_new_row)
            self.water_quality_reports.setEnabled(not is_new_row)
        else:
            self.show_data_btn.setEnabled(False)
            self.construction_logs_manager.setEnabled(False)
            self.water_quality_reports.setEnabled(False)

    # ---- Timeseries
    def get_current_obs_well_data(self):
        """
        Return the observation well data relative to the currently selected
        rows in the table.
        """
        try:
            return self.tableview.get_current_row_data().iloc[0]
        except AttributeError:
            return None

    def _create_extra_toolbuttons(self):
        # Setup show data button.
        self.show_data_btn = create_toolbutton(
            self,
            icon='show_data_table',
            text=_("View data"),
            tip=_('Open a table showing all readings saved in the database '
                  'for the currently selected observation well.'),
            triggered=self._view_current_timeseries_data,
            iconsize=get_iconsize()
            )

        # Setup show in Google map button.
        self.show_gmap_btn = create_toolbutton(
            self,
            icon='map_search',
            text=_("Show in Google Maps"),
            tip=_("Show the currently selected observation "
                  "well in Google Maps."),
            triggered=self.show_in_google_maps,
            iconsize=get_iconsize()
            )

        # Setup construction logs manager.
        self.construction_logs_manager = FileAttachmentManager(
            self, icon='construction_log', attachment_type=1,
            qfiledialog_namefilters=(
                _('Construction Log') +
                ' (*.png ; *.bmp ; *.jpg ; *.jpeg ; *.tif ; *.pdf)'),
            qfiledialog_title=_(
                'Select a Construction Log for Station {}'),
            text=_("Construction Logs"),
            tooltip=_(
                "Open the menu to add a construction log to the currently "
                "selected station or to view or delete an existing "
                "construction log."),
            attach_text=_("Attach Construction Log..."),
            attach_tooltip=_(
                "Attach a construction log to the currently "
                "selected station."),
            show_text=_("Show Construction Log..."),
            show_tooltip=_(
                "Show the construction log attached to the currently "
                "selected station."),
            remove_text=_("Remove Construction Log"),
            remove_tooltip=_(
                "Remove the construction log attached to the currently "
                "selected station.")
            )

        # Setup water quality reports manager.
        self.water_quality_reports = FileAttachmentManager(
            self, icon='water_quality', attachment_type=2,
            qfiledialog_namefilters=(
                _('Water Quality Report') +
                ' (*.xls ; *.xlsx ; *.csv, ; *.txt)'),
            qfiledialog_title=_(
                'Select a water quality report for Station {}'),
            text=_("Water Quality Report"),
            tooltip=_(
                "Open the menu to add a water quality report to the currently "
                "selected station or to view or delete an existing "
                "report."),
            attach_text=_("Attach Water Quality Report..."),
            attach_tooltip=_(
                "Attach a water quality report to the currently "
                "selected station."),
            show_text=_("Show Water Quality Report..."),
            show_tooltip=_(
                "Show the water quality report attached to the "
                "currently selected station."),
            remove_text=_("Remove Water Quality Report"),
            remove_tooltip=_(
                "Remove the water quality report attached to the "
                "currently selected station.")
            )

        return [self.show_data_btn, self.show_gmap_btn,
                self.construction_logs_manager.toolbutton,
                self.water_quality_reports.toolbutton]

    def _view_current_timeseries_data(self):
        """
        Emit a signal to show the timeseries data saved in the database for
        the currently selected observation well in the table.
        """
        current_obs_well_data = self.get_current_obs_well_data()
        if current_obs_well_data is not None:
            self.sig_view_data.emit(current_obs_well_data.name, False)

    def show_in_google_maps(self):
        """
        Search the monitoring station in Google map on the
        appropriate Web browser for the user’s desktop environment.

        https://developers.google.com/maps/documentation/urls/get-started
        """
        current_obs_well_data = self.get_current_obs_well_data()
        if current_obs_well_data is not None:
            lat_dd = current_obs_well_data['latitude']
            lon_dd = current_obs_well_data['longitude']
            url = ("https://www.google.com/maps/search/"
                   "?api=1&query={},{}"
                   ).format(lat_dd, lon_dd)
            return QDesktopServices.openUrl(QUrl(url))
        return False
