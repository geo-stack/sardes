# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Standard imports
import datetime as dtm
import os.path as osp

# ---- Third party imports
import pandas as pd

# ---- Local imports
from sardes.config.locale import _


def format_kml_station_info(
        station_data: pd.DataFrame, ground_altitude: float,
        is_alt_geodesic: bool, last_reading: dtm.datetime = None
        ) -> str:
    """
    Format the description of the station for the info buble of the kml file.
    """
    is_station_active = (
        _('Active') if station_data['is_station_active'] else _('Inactive'))
    is_influenced = {
        0: _('No'), 1: _('Yes'), 2: _('NA')
        }[station_data['is_influenced']]

    desc = '{} = {}<br/>'.format(
        _('Station'), station_data['obs_well_id'])

    desc += '{} = {:0.4f}<br/>'.format(
        _('Longitude'), station_data['longitude'])
    desc += '{} = {:0.4f}<br/>'.format(
        _('Latitude'), station_data['latitude'])

    desc += '{} = {:0.2f} {} ({})<br/>'.format(
        _('Ground Alt.'), ground_altitude, _('m MSL'),
        _('Geodesic') if is_alt_geodesic else _('Approximate')
        )

    desc += '{} = {}<br/>'.format(
        _('Water-table'), station_data['confinement'])

    desc += '{} = {}<br/><br/>'.format(
        _('Influenced'), is_influenced)

    if last_reading is not None:
        desc += '{} = {}<br/>'.format(
            _('Last reading'), last_reading.strftime('%Y-%m-%d'))

    desc += '{} = {}<br/>'.format(
        _('Status'), is_station_active)

    return desc
