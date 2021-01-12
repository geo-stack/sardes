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
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QMenu

# ---- Local imports
from sardes.api.tablemodels import SardesTableModel
from sardes.config.gui import get_iconsize
from sardes.config.locale import _
from sardes.utils.qthelpers import create_toolbutton, create_action
from sardes.widgets.tableviews import (
    SardesTableWidget, StringEditDelegate, BoolEditDelegate,
    NumEditDelegate, NotEditableDelegate, TextEditDelegate)


class ObsWellsTableModel(SardesTableModel):
    """
    A table model to display the list of observation wells that are saved
    in the database.
    """

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
        table_model = ObsWellsTableModel(
            table_title=_('Observation Wells'),
            table_id='table_observation_wells',
            data_columns_mapper=[
                ('obs_well_id', _('Well ID')),
                ('common_name', _('Common Name')),
                ('municipality', _('Municipality')),
                ('aquifer_type', _('Aquifer')),
                ('aquifer_code', _('Aquifer Code')),
                ('confinement', _('Confinement')),
                ('in_recharge_zone', _('Recharge Zone')),
                ('is_influenced', _('Influenced')),
                ('latitude', _('Latitude')),
                ('longitude', _('Longitude')),
                ('first_date', _('First Date')),
                ('last_date', _('Last Date')),
                ('mean_water_level', _('Mean level (m)')),
                ('is_station_active', _('Active')),
                ('obs_well_notes', _('Notes'))]
            )
        super().__init__(table_model, *args, **kargs)

        self.add_toolbar_separator()
        for button in self._create_extra_toolbuttons():
            self.add_toolbar_widget(button)

    # ---- SardesPaneWidget public API
    def register_to_plugin(self, plugin):
        """Register this table with the given plugin."""
        self.sig_view_data.connect(plugin.main.view_timeseries_data)

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

        # Setup construction log button.
        self.construction_log_btn = create_toolbutton(
            self,
            icon='water_well',
            text=_("Construction Log"),
            iconsize=get_iconsize())

        attach_construction_log_action = create_action(
            self,
            _("Attach Construction Log"),
            tip=_("Attach a construction log file to the "
                  "currently selected observation well."),
            icon='attachment',
            triggered=self._handle_attach_drillog_request)
        self.show_construction_log_action = create_action(
            self,
            _("Show Construction Log"),
            tip=_("Show the construction log file attached to the "
                  "currently selected observation well."),
            icon='magnifying_glass',
            triggered=self._handle_show_drillog_request)

        construction_log_menu = QMenu()
        construction_log_menu.addAction(attach_construction_log_action)
        construction_log_menu.addAction(self.show_construction_log_action)

        self.construction_log_btn.setMenu(construction_log_menu)
        self.construction_log_btn.setPopupMode(
            self.construction_log_btn.InstantPopup)

        return [self.show_data_btn, self.construction_log_btn]

    def _view_current_timeseries_data(self):
        """
        Emit a signal to show the timeseries data saved in the database for
        the currently selected observation well in the table.
        """
        current_obs_well_data = self.get_current_obs_well_data()
        if current_obs_well_data is not None:
            self.sig_view_data.emit(current_obs_well_data.name, False)

    def _handle_attach_drillog_request(self):
        """
        Handle when a request is made by the user to attach a drillog to
        the currently selected station.
        """
        pass

    def _handle_show_drillog_request(self):
        """
        Handle when a request is made by the user to show the drillog attached
        to the currently selected station.
        """
        pass
