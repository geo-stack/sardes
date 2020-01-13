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
import numpy as np


def nan_values_equal(x1, x2):
    """
    Return wheter two Python objects x1 and x2 are equal or not. Account for
    the fact that the equality of two numpy nan values is False.
    """
    try:
        isnan1 = np.isnan(x1)
        isnan2 = np.isnan(x2)
    except TypeError:
        isnan1 = False
        isnan2 = False
    else:
        isnan1 = False if isinstance(isnan1, np.ndarray) else isnan1
        isnan2 = False if isinstance(isnan2, np.ndarray) else isnan2
    return x1 == x2 or (isnan1 and isnan2)


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
