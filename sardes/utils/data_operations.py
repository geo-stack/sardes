# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Stantard imports
import itertools

# ---- Third party imports
from numpy import nan
import pandas as pd

# ---- Local imports
from sardes.api.timeseries import DataType


def are_values_equal(x1, x2):
    """
    Return wheter two Python objects x1 and x2 are equal or not. Account for
    the fact that the equality of two numpy nan values is False.
    """
    try:
        isnull_x1 = pd.isnull(x1)
        isnull_x2 = pd.isnull(x2)
    except TypeError:
        isnull_x1 = False
        isnull_x2 = False
    if isnull_x1 or isnull_x2:
        return isnull_x1 and isnull_x2
    else:
        return x1 == x2


def intervals_extract(iterable):
    """
    Given a list of sequential numbers, convert the given list into
    a list of intervals.

    Code adapted from:
    https://www.geeksforgeeks.org/python-make-a-list-of-intervals-with-sequential-numbers/
    """
    sequence = sorted(set(iterable))
    for key, group in itertools.groupby(enumerate(sequence),
                                        lambda v: v[1] - v[0]):
        group = list(group)
        yield [group[0][1], group[-1][1]]


def format_reading_data(data, repere_data):
    """
    Format readings data for publication.
    """
    if data.empty:
        return data

    # Convert water level in altitude (above see level).
    if not repere_data.empty:
        for i in range(len(repere_data)):
            repere_iloc = repere_data.iloc[i]
            reference_altitude = repere_iloc['top_casing_alt']
            start_date = repere_iloc['start_date']
            end_date = repere_iloc['end_date']
            if pd.isnull(end_date):
                indexes = data.index[data['datetime'] >= start_date]
            else:
                indexes = data.index[
                    (data['datetime'] >= start_date) &
                    (data['datetime'] < end_date)]
            data.loc[indexes, DataType.WaterLevel] = (
                reference_altitude - data.loc[indexes, DataType.WaterLevel])

    # Resample data on a daily basis and remove duplicate values if any.
    data = (
        data
        .dropna(subset=[DataType.WaterLevel])
        # We keep the readings closest to midnight.
        .groupby('obs_id').resample('D', on='datetime').first()
        .dropna(subset=[DataType.WaterLevel])
        .droplevel(0, axis=0).drop('datetime', axis=1)
        .reset_index(drop=False)
        .sort_values(by=['datetime', 'install_depth'],
                     ascending=[True, True])
        # We keep the reading measured closest to the surface.
        .drop_duplicates(subset='datetime', keep='first')
        .reset_index(drop=True)
        )

    return data
