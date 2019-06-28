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
import pytest
from qtpy.QtCore import QPoint, QSize

# ---- Local imports
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


def test_mainwindow_settings(qtbot, mocker):
    """
    Test that the window size and position are store and restore correctly
    in and from our configs.
    """
    mainwindow1 = MainWindow()
    mainwindow1.show()
    qtbot.waitForWindowShown(mainwindow1)

    # Assert the default values.
    assert mainwindow1.size() == QSize(900, 450)
    assert mainwindow1.pos() == QPoint(50, 50)
    assert not mainwindow1.isMaximized()
    assert mainwindow1.get_window_settings() == ((900, 450), (50, 50), False)

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
