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


def intervals_extract(iterable):
    """
    Given a list of sequential numbers, convert the given list into
    a list of intervals.

    Code adapted from:
    https://www.geeksforgeeks.org/python-make-a-list-of-intervals-with-sequential-numbers/
    """
    sequence = sorted(set(iterable))
    intervals = []
    for key, group in itertools.groupby(enumerate(sequence),
                                        lambda v: v[1] - v[0]):
        group = list(group)
        intervals.append([group[0][1], group[-1][1]])
    return intervals
