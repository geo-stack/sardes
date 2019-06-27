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

# ---- Third party imports
import pytest
from qtpy.QtCore import QPoint, QSize
from appconfigs.user import UserConfig

# ---- Local imports
from sardes.app.mainwindow import MainWindow
from sardes.config.main import CONF_VERSION, DEFAULTS


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def CONF(tmpdir, mocker):
    CONFIG_DIR = str(tmpdir)
    CONF = UserConfig('sardes', defaults=DEFAULTS, load=True,
                      version=CONF_VERSION, path=CONFIG_DIR,
                      backup=True, raw_mode=True)
    mocker.patch('sardes.config.main.CONF', new=CONF)
    mocker.patch('sardes.config.gui.CONF', new=CONF)
    return CONF


@pytest.fixture
def mainwindow(CONF, qtbot, mocker):
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
