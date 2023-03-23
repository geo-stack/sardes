# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Third party imports
import numpy as np
import pandas as pd
from qtpy.QtCore import Signal, QUrl
from qtpy.QtGui import QDesktopServices

# ---- Local imports
from sardes.api.tablemodels import (
    SardesTableColumn, sardes_table_column_factory)
from sardes.config.gui import get_iconsize
from sardes.config.locale import _
from sardes.utils.qthelpers import create_toolbutton
from sardes.widgets.tableviews import SardesTableWidget
from sardes.tables.models import StandardSardesTableModel
from sardes.tables.managers import FileAttachmentManager
from sardes.tables.delegates import (
    StringEditDelegate, BoolEditDelegate, DateTimeDelegate,
    NumEditDelegate, NotEditableDelegate, TextEditDelegate,
    TriStateEditDelegate)
from sardes.tables.errors import ForeignReadingsConstraintError
from sardes.tools.waterquality import WaterQualityReportTool


class ObsWellsTableModel(StandardSardesTableModel):
    """
    A table model to display the list of observation wells that are saved
    in the database.
    """
    __tablename__ = 'table_observation_wells'
    __tabletitle__ = _('Observation Wells')
    __tablecolumns__ = [
        sardes_table_column_factory(
            'observation_wells_data', 'obs_well_id', _('Well ID'),
            delegate=StringEditDelegate
            ),
        sardes_table_column_factory(
            'observation_wells_data', 'common_name', _('Common Name'),
            delegate=StringEditDelegate
            ),
        sardes_table_column_factory(
            'observation_wells_data', 'municipality', _('Municipality'),
            delegate=StringEditDelegate
            ),
        sardes_table_column_factory(
            'observation_wells_data', 'aquifer_type', _('Aquifer'),
            delegate=StringEditDelegate
            ),
        sardes_table_column_factory(
            'observation_wells_data', 'aquifer_code', _('Aquifer Code'),
            delegate=NumEditDelegate,
            delegate_options={
                'decimals': 0, 'minimum': 0, 'maximum': 999}
            ),
        sardes_table_column_factory(
            'observation_wells_data', 'confinement', _('Confinement'),
            delegate=StringEditDelegate
            ),
        sardes_table_column_factory(
            'observation_wells_data', 'in_recharge_zone', _('Recharge Zone'),
            delegate=TriStateEditDelegate
            ),
        sardes_table_column_factory(
            'observation_wells_data', 'is_influenced', _('Influenced'),
            delegate=TriStateEditDelegate
            ),
        sardes_table_column_factory(
            'observation_wells_data', 'latitude', _('Latitude'),
            delegate=NumEditDelegate,
            delegate_options={'decimals': 16, 'minimum': -180, 'maximum': 180},
            ),
        sardes_table_column_factory(
            'observation_wells_data', 'longitude', _('Longitude'),
            delegate=NumEditDelegate,
            delegate_options={'decimals': 16, 'minimum': -180, 'maximum': 180},
            ),
        SardesTableColumn(
            'first_date', _('First Date'), 'datetime64[ns]',
            editable=False,
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd"},
            ),
        SardesTableColumn(
            'last_date', _('Last Date'), 'datetime64[ns]',
            editable=False,
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd"},
            ),
        SardesTableColumn(
            'mean_water_level', _('Mean level (m)'), 'float64',
            editable=False,
            delegate=NotEditableDelegate
            ),
        sardes_table_column_factory(
            'observation_wells_data', 'is_station_active', _('Active'),
            delegate=BoolEditDelegate
            ),
        sardes_table_column_factory(
            'observation_wells_data', 'obs_well_notes', _('Notes'),
            delegate=TextEditDelegate
            )
        ]

    __dataname__ = 'observation_wells_data'
    __libnames__ = ['observation_wells_data_overview', 'attachments_info',
                    'hg_surveys']

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

    # ---- Visual Data
    def logical_to_visual_data(self, visual_dataf):
        """
        Transform logical data to visual data.
        """
        try:
            obs_wells_stats = self.libraries['observation_wells_data_overview']
        except KeyError:
            for column in ['first_date', 'last_date']:
                visual_dataf[column] = pd.NaT
        else:
            for column in ['first_date', 'last_date', 'mean_water_level']:
                if column in obs_wells_stats.columns:
                    visual_dataf[column] = obs_wells_stats[column]
                else:
                    visual_dataf[column] = (
                        np.nan if column == 'mean_water_level' else pd.NaT)
        return super().logical_to_visual_data(visual_dataf)


class ObsWellsTableWidget(SardesTableWidget):
    sig_view_data = Signal(object, bool)

    def __init__(self, *args, **kargs):
        table_model = ObsWellsTableModel()
        super().__init__(table_model, *args, **kargs)

        self.add_toolbar_separator()
        for button in self._create_extra_toolbuttons():
            self.add_toolbar_widget(button)

        self.water_quality_report_tool = WaterQualityReportTool(self)
        self.install_tool(self.water_quality_report_tool)

    # ---- SardesPaneWidget public API
    def register_to_plugin(self, plugin):
        """Register this table with the given plugin."""
        self.sig_view_data.connect(plugin.main.view_timeseries_data)
        self.construction_logs_manager.set_dbmanager(
            plugin.main.db_connection_manager)

    # ---- SardesTableWidget public API
    def on_current_changed(self, current_index):
        """
        Extend base SardesTableWidget method.
        """
        if current_index.isValid():
            is_new_row = self.model().is_new_row_at(current_index)
            self.show_data_btn.setEnabled(not is_new_row)
            self.construction_logs_manager.setEnabled(not is_new_row)
        else:
            self.show_data_btn.setEnabled(False)
            self.construction_logs_manager.setEnabled(False)
        super().on_current_changed(current_index)

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

        return [self.show_data_btn, self.show_gmap_btn,
                self.construction_logs_manager.toolbutton]

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
