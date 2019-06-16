# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the mainwindow.
"""

# ---- Standard imports
import os
from unittest.mock import Mock

# ---- Third party imports
import psycopg2
import pytest
from qtpy.QtCore import Qt

# ---- Local imports
from sardes.app.mainwindow import MainWindow


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def mainwindow(qtbot, mocker):
    mainwindow = MainWindow()
    qtbot.addWidget(mainwindow)
    mainwindow.show()
    return mainwindow


# =============================================================================
# ---- Tests for MainWindow
# =============================================================================
def test_mainwindow_init(mainwindow):
    """Test that the main window is initialized correctly."""
    assert mainwindow


if __name__ == "__main__":
    pytest.main(['-x', os.path.basename(__file__), '-v', '-rw'])
