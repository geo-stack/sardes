# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Standard imports
import os
import os.path as osp
import tempfile

# ---- Third party imports
import pandas as pd
from qtpy.QtCore import Signal, QObject, QUrl
from qtpy.QtGui import QDesktopServices
from qtpy.QtWidgets import QMenu, QFileDialog

# ---- Local imports
from sardes.api.tablemodels import StandardSardesTableModel, SardesTableColumn
from sardes.config.gui import get_iconsize
from sardes.config.locale import _
from sardes.config.main import TEMP_DIR
from sardes.config.ospath import (
    get_select_file_dialog_dir, set_select_file_dialog_dir)
from sardes.utils.qthelpers import create_toolbutton, create_action
from sardes.widgets.tableviews import (
    SardesTableWidget, StringEditDelegate, BoolEditDelegate,
    NumEditDelegate, NotEditableDelegate, TextEditDelegate)


class ObsWellsTableModel(StandardSardesTableModel):
    """
    A table model to display the list of observation wells that are saved
    in the database.
    """
    __tablename__ = 'table_observation_wells'
    __tabletitle__ = _('Observation Wells')
    __tablecolumns__ = [
        SardesTableColumn(
            'obs_well_id', _('Well ID'), 'str', notnull=True, unique=True),
        SardesTableColumn(
            'common_name', _('Common Name'), 'str'),
        SardesTableColumn(
            'municipality', _('Municipality'), 'str'),
        SardesTableColumn(
            'aquifer_type', _('Aquifer'), 'str'),
        SardesTableColumn(
            'aquifer_code', _('Aquifer Code'), 'Int64'),
        SardesTableColumn(
            'confinement', _('Confinement'), 'str'),
        SardesTableColumn(
            'in_recharge_zone', _('Recharge Zone'), 'str'),
        SardesTableColumn(
            'is_influenced', _('Influenced'), 'str'),
        SardesTableColumn(
            'latitude', _('Latitude'), 'float64'),
        SardesTableColumn(
            'longitude', _('Longitude'), 'float64'),
        SardesTableColumn(
            'first_date', _('First Date'), 'datetime64[ns]'),
        SardesTableColumn(
            'last_date', _('Last Date'), 'datetime64[ns]'),
        SardesTableColumn(
            'mean_water_level', _('Mean level (m)'), 'float64'),
        SardesTableColumn(
            'is_station_active', _('Active'), 'boolean', notnull=True),
        SardesTableColumn(
            'obs_well_notes', _('Notes'), dtype='str')]

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

    def create_delegate_for_column(self, view, column):
        """
        Create the item delegate that the view need to use when editing the
        data of this model for the specified column. If None is returned,
        the items of the column will not be editable.
        """
        if column in ['is_station_active']:
            return BoolEditDelegate(view, is_required=True)
        elif column in ['obs_well_id']:
            return StringEditDelegate(view, unique_constraint=True,
                                      is_required=True)
        elif column in ['municipality', 'is_influenced', 'common_name',
                        'in_recharge_zone', 'confinement', 'aquifer_type']:
            return StringEditDelegate(view)
        elif column in ['aquifer_code']:
            return NumEditDelegate(view, decimals=0, bottom=0, top=999)
        elif column in ['obs_well_notes']:
            return TextEditDelegate(view)
        elif column in ['latitude', 'longitude']:
            return NumEditDelegate(view, 16, -180, 180)
        else:
            return NotEditableDelegate(view)

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


class FileAttachmentManager(QObject):
    """
    A class to handle adding, viewing, and removing file attachments
    in the database.
    """
    sig_attach_request = Signal(object, object, object)

    sig_attachment_added = Signal()
    sig_attachment_shown = Signal()
    sig_attachment_removed = Signal()

    def __init__(self, tablewidget, icon, attachment_type,
                 qfiledialog_namefilters, qfiledialog_title,
                 text, tooltip, attach_text, attach_tooltip, show_text,
                 show_tooltip, remove_text, remove_tooltip):
        super().__init__()
        self._enabled = True
        self.dbmanager = None

        self.tablewidget = tablewidget
        self.attachment_type = attachment_type

        self.qfiledialog_namefilters = qfiledialog_namefilters
        self.qfiledialog_title = qfiledialog_title

        self.toolbutton = create_toolbutton(
            tablewidget, text=text, tip=tooltip, icon=icon,
            iconsize=get_iconsize())
        self.attach_action = create_action(
            tablewidget, text=attach_text, tip=attach_tooltip,
            icon='attachment', triggered=self._handle_attach_request)
        self.show_action = create_action(
            tablewidget, text=show_text, tip=show_tooltip,
            icon='magnifying_glass', triggered=self._handle_show_request)
        self.remove_action = create_action(
            tablewidget, text=remove_text, tip=remove_tooltip,
            icon='delete_data', triggered=self._handle_remove_request)

        menu = QMenu()
        menu.addAction(self.attach_action)
        menu.addAction(self.show_action)
        menu.addAction(self.remove_action)
        menu.aboutToShow.connect(self._handle_menu_aboutToShow)

        self.toolbutton.setMenu(menu)
        self.toolbutton.setPopupMode(self.toolbutton.InstantPopup)

    # ---- Qt widget interface emulation
    def isEnabled(self):
        """
        Treturn whether this file attachment manager is enabled.
        """
        return self._enabled

    def setEnabled(self, enabled):
        """
        Set this file attachment manager state to the provided enabled value.
        """
        self._enabled = bool(enabled)
        self.toolbutton.setEnabled(self._enabled)

    def set_dbmanager(self, dbmanager):
        """
        Set the database manager for this file attachment manager.
        """
        self.dbmanager = dbmanager

    # ---- Convenience Methods
    def current_station_id(self):
        """
        Return the id of the station that is currently selected
        in the table in which this file attachment manager is installed.
        """
        station_data = self.tablewidget.get_current_obs_well_data()
        if station_data is None:
            return None
        else:
            return station_data.name

    def current_station_name(self):
        """
        Return the name of the station that is currently selected
        in the table in which this file attachment manager is installed.
        """
        station_data = self.tablewidget.get_current_obs_well_data()
        return station_data['obs_well_id']

    def is_attachment_exists(self):
        """
        Return whether an attachment exists in the database for the
        currently selected station in the table.
        """
        return bool((
            self.tablewidget.model().libraries['stored_attachments_info'] ==
            [self.current_station_id(), self.attachment_type]
            ).all(1).any())

    # ---- Handlers
    def _handle_menu_aboutToShow(self):
        """
        Handle when the menu is about to be shown so that we can
        disable/enable the items depending on the availability or
        not of an attachment for the currently selected station.
        """
        self.tablewidget.tableview.setFocus()
        station_id = self.current_station_id()
        if station_id is None:
            self.attach_action.setEnabled(False)
            self.show_action.setEnabled(False)
            self.remove_action.setEnabled(False)
        else:
            is_attachment_exists = self.is_attachment_exists()
            self.attach_action.setEnabled(True)
            self.show_action.setEnabled(is_attachment_exists)
            self.remove_action.setEnabled(is_attachment_exists)

    def _handle_attach_request(self):
        """
        Handle when a request is made by the user to add an attachment
        to the currently selected station.
        """
        filename, filefilter = QFileDialog.getOpenFileName(
            self.tablewidget.parent() or self.tablewidget,
            self.qfiledialog_title.format(self.current_station_name()),
            get_select_file_dialog_dir(),
            self.qfiledialog_namefilters)
        if filename:
            set_select_file_dialog_dir(osp.dirname(filename))
            if self.dbmanager is not None:
                station_id = self.current_station_id()
                self.dbmanager.set_attachment(
                    station_id, self.attachment_type, filename,
                    callback=self.sig_attachment_added.emit)

    def _handle_show_request(self):
        """
        Handle when a request is made by the user to show the attachment
        of the currently selected station.
        """
        if self.dbmanager is not None:
            station_id = self.current_station_id()
            self.dbmanager.get_attachment(
                station_id,
                self.attachment_type,
                callback=self._open_attachment_in_external)

    def _handle_remove_request(self):
        """
        Handle when a request is made by the user to remove the attachment
        of the currently selected station.
        """
        if self.dbmanager is not None:
            station_id = self.current_station_id()
            self.dbmanager.del_attachment(
                station_id,
                self.attachment_type,
                callback=self.sig_attachment_removed.emit)

    # ---- Callbacks
    def _open_attachment_in_external(self, data, name):
        """
        Open the attachment file in an external application that is
        chosen by the OS.
        """
        temp_path = tempfile.mkdtemp(dir=TEMP_DIR)
        temp_filename = osp.join(temp_path, name)
        with open(temp_filename, 'wb') as f:
            f.write(data)
        os.startfile(temp_filename)
        self.sig_attachment_shown.emit()
