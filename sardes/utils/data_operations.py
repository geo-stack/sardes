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


def format_reading_data(data, reference_altitude=None):
    """
    Format readings data for publication.
    """
    data = (
        data
        .dropna(subset=[DataType.WaterLevel])
        # We need to replace nan values by a placeholder float to avoid
        # the bug that was reported in #cgq-qgc/sardes#362.
        .fillna({'install_depth': -999})
        # For each day, we keep the reading closest to midnight.
        .groupby('install_depth').resample('D', on='datetime').first()
        .dropna(subset=[DataType.WaterLevel])
        .droplevel(0, axis=0).drop('datetime', axis=1)
        .reset_index(drop=False)
        .sort_values(by=['datetime', 'install_depth'],
                     ascending=[True, True])
        # We keep the reding measured closest to the surface.
        .drop_duplicates(subset='datetime', keep='first')
        .reset_index(drop=True)
        )
    data['install_depth'] = data['install_depth'].replace({-999: nan})

    # Convert water level in altitude.
    if reference_altitude is not None:
        data[DataType.WaterLevel] = (
            reference_altitude - data[DataType.WaterLevel])
    return data
