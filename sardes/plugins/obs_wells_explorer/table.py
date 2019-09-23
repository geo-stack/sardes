# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Local imports
from sardes.widgets.tableviews import (
    SardesTableModel, StringEditDelegate, BoolEditDelegate, NumEditDelegate,
    NotEditableDelegate, TextEditDelegate)
from sardes.config.locale import _


class ObsWellsTableModel(SardesTableModel):
    """
    A table model to display the list of observation wells that are saved
    in the database.
    """
    # A list of tuple that maps the keys of the columns dataframe with their
    # corresponding human readable label to use in the GUI.
    __data_columns_mapper__ = [
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
        ('is_station_active', _('Active')),
        ('obs_well_notes', _('Note'))
        ]

    def fetch_model_data(self):
        self.db_connection_manager.get_observation_wells_data(
            callback=self.set_model_data)

    # ---- Delegates
    def create_delegate_for_column(self, view, column):
        if column in ['is_station_active']:
            return BoolEditDelegate(view)
        elif column in ['obs_well_id', 'common_name']:
            return StringEditDelegate(view, unique_constraint=True)
        elif column in ['municipality', 'is_influenced',
                        'in_recharge_zone', 'confinement']:
            return StringEditDelegate(view)
        elif column in ['obs_well_notes']:
            return TextEditDelegate(view)
        elif column in ['obs_well_id']:
            return NotEditableDelegate(view)
        elif column in ['latitude', 'longitude']:
            return NumEditDelegate(view, 16, -180, 180)
        else:
            return NotEditableDelegate(view)
