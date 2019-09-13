# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Local imports
from sardes.widgets.tableviews import (SardesTableView, StringEditDelegate,
                                       BoolEditDelegate, ComboBoxDelegate,
                                       FloatEditDelegate)
from sardes.config.locale import _


class ObsWellsTableView(SardesTableView):
    """
    A table to display the list of observation wells that are saved
    in the database.
    """
    # A list of tuple that maps the keys of the columns dataframe with their
    # corresponding human readable label to use in the GUI.
    DATA_COLUMNS_MAPPER = [
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

    # The name of the method that the database connection manager need to call
    # to retrieve the data from the database for this table view.
    GET_DATA_METHOD = 'get_observation_wells_data'

    # ---- Delegates
    def create_delegate_for_column(self, column):
        """
        Create the item delegate that this model's table view need to use
        for the specified column. If None is returned, the items of the
        column will not be editable.
        """
        if column in ['is_station_active']:
            return BoolEditDelegate(self)
        elif column in ['obs_well_id']:
            return None
        elif column in ['latitude', 'longitude']:
            return FloatEditDelegate(self, -180, 180, 16)
        else:
            return StringEditDelegate(self)
