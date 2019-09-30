# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the data operations functions.
"""

# ---- Standard imports
import os

# ---- Third party imports
import pytest

# ---- Local imports
from sardes.utils.data_operations import intervals_extract


# =============================================================================
# ---- Tests
# =============================================================================
def test_intervals_extract():
    """Test that the function intervals_extract is working as expected."""
    sequence = [2, 3, 4, 5, 7, 8, 9, 11, 15, 16]
    expected_result = [[2, 5], [7, 9], [11, 11], [15, 16]]
    assert list(intervals_extract(sequence)) == expected_result


if __name__ == "__main__":
    pytest.main(['-x', os.path.basename(__file__), '-v', '-rw', '-s'])
