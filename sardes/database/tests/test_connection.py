# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for database/connection.py.
"""

# ---- Standard imports
import os

# ---- Third party imports
import pytest

# ---- Local imports
from sardes.database.connection import BDConnManager


# =============================================================================
# ---- Tests
# =============================================================================
def test_dbconnmanager_init(qtbot):
    """Test that the BDConnManager can be initialized correctly."""
    db_conn_manager = BDConnManager()
    assert db_conn_manager


if __name__ == "__main__":
    pytest.main(['-x', os.path.basename(__file__), '-v', '-rw'])
