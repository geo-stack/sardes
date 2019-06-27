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


def test_mainwindow_settings(CONF, qtbot, tmpdir, mocker):
    """
    Test that the window size and position are store and restore correctly
    in and from our configs.
    """
    mainwindow1 = MainWindow()
    qtbot.addWidget(mainwindow1)
    mainwindow1.show()
    qtbot.waitForWindowShown(mainwindow1)

    # Assert the default values.
    assert mainwindow1.size() == QSize(1260, 740)
    assert mainwindow1.pos() == QPoint(50, 50)
    assert not mainwindow1.isMaximized()
    assert mainwindow1.get_window_settings() == ((1260, 740), (50, 50), False)

    # Resize and move the window to some expected size and position value.
    expected_normal_window_size = (650, 400)
    expected_normal_window_pos = (100, 100)
    mainwindow1.resize(*expected_normal_window_size)
    mainwindow1.move(*expected_normal_window_pos)

    assert mainwindow1.size() == QSize(*expected_normal_window_size)
    assert mainwindow1.pos() == QPoint(*expected_normal_window_pos)
    assert not mainwindow1.isMaximized()
    assert mainwindow1.get_window_settings() == (
        expected_normal_window_size, expected_normal_window_pos, False)

    # Maximize the window.
    mainwindow1.showMaximized()
    qtbot.wait(5)

    assert mainwindow1.size() != QSize(*expected_normal_window_size)
    assert mainwindow1.pos() != QPoint(*expected_normal_window_pos)
    assert mainwindow1.isMaximized()
    assert mainwindow1.get_window_settings() == (
        expected_normal_window_size, expected_normal_window_pos, True)

    # Close and delete the window.
    with qtbot.waitSignal(mainwindow1.destroyed):
        mainwindow1.close()
        mainwindow1.deleteLater()

    # Create a new instance of the main window.
    mainwindow2 = MainWindow()
    mainwindow2.show()
    qtbot.waitForWindowShown(mainwindow2)

    assert mainwindow2.size() != QSize(*expected_normal_window_size)
    assert mainwindow2.pos() != QPoint(*expected_normal_window_pos)
    assert mainwindow2.isMaximized()
    assert mainwindow2.get_window_settings() == (
        expected_normal_window_size, expected_normal_window_pos, True)


if __name__ == "__main__":
    pytest.main(['-x', os.path.basename(__file__), '-v', '-rw'])
