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
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
from flaky import flaky
import pytest
from qtpy.QtCore import QPoint, QSize

# ---- Local imports
from sardes.config.gui import INIT_MAINWINDOW_SIZE
from sardes.config.main import CONF
from sardes.app.mainwindow import MainWindow, QMessageBox


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def mainwindow(qtbot, mocker):
    """A fixture for Sardes main window."""
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


@flaky(max_runs=3)
def test_mainwindow_settings(qtbot, mocker):
    """
    Test that the window size and position are store and restore correctly
    in and from our configs.
    """
    CONF.set('main', 'window/geometry', None)

    mainwindow1 = MainWindow()
    qtbot.addWidget(mainwindow1)
    mainwindow1.show()
    qtbot.waitForWindowShown(mainwindow1)

    # Assert the default values.
    assert mainwindow1.size() == QSize(*INIT_MAINWINDOW_SIZE)
    assert not mainwindow1.isMaximized()

    # Resize and move the window to some expected size and position value.
    expected_normal_window_size = (650, 400)
    expected_normal_window_pos = (mainwindow1.x() + 25, mainwindow1.y() + 25)
    mainwindow1.resize(*expected_normal_window_size)
    mainwindow1.move(*expected_normal_window_pos)

    assert mainwindow1.size() == QSize(*expected_normal_window_size)
    assert mainwindow1.pos() == QPoint(*expected_normal_window_pos)
    assert not mainwindow1.isMaximized()

    # Maximize the window.
    mainwindow1.showMaximized()
    qtbot.wait(100)

    assert mainwindow1.size() != QSize(*expected_normal_window_size)
    assert mainwindow1.pos() != QPoint(*expected_normal_window_pos)
    assert mainwindow1.isMaximized()

    # Close the main window.
    assert CONF.get('main', 'window/geometry', None) is None
    mainwindow1_size = mainwindow1.size()
    mainwindow1_pos = mainwindow1.pos()
    mainwindow1.close()
    assert CONF.get('main', 'window/geometry', None) is not None
    qtbot.wait(100)

    # Create a new instance of the main window and assert that the size,
    # position and maximized state were restored from the previous
    # mainwindow that was closed.
    mainwindow2 = MainWindow()
    qtbot.addWidget(mainwindow2)
    mainwindow2.show()
    qtbot.waitForWindowShown(mainwindow2)
    qtbot.wait(100)

    assert mainwindow2.size() == mainwindow1_size
    assert mainwindow2.pos() == mainwindow1_pos
    assert mainwindow2.isMaximized()


def test_mainwindow_lang_change(mainwindow, qtbot, mocker):
    """
    Test that the window size and position are store and restore correctly
    in and from our configs.
    """
    # Check that English is the default selected language.
    lang_actions = mainwindow.lang_menu.actions()
    checked_actions = [act for act in lang_actions if act.isChecked()]
    assert len(lang_actions) == 2
    assert len(checked_actions) == 1
    assert checked_actions[0].text() == 'English'

    # Change the language to French.
    mocker.patch.object(QMessageBox, 'information')
    fr_action = [act for act in lang_actions if act.text() == 'Français'][0]
    fr_action.toggle()

    # Close and delete the window.
    mainwindow.close()
    qtbot.wait(5)

    # Create a new instance of the main window and assert that the
    # language was changed for Français.
    mainwindow_restart = MainWindow()
    qtbot.addWidget(mainwindow_restart)
    mainwindow_restart.show()
    qtbot.waitForWindowShown(mainwindow_restart)

    lang_actions = mainwindow_restart.lang_menu.actions()
    checked_actions = [act for act in lang_actions if act.isChecked()]
    assert len(checked_actions) == 1
    assert checked_actions[0].text() == 'Français'


if __name__ == "__main__":
    pytest.main(['-x', os.path.basename(__file__), '-v', '-rw'])
