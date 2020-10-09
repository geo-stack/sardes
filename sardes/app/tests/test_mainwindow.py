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
from qtpy.QtCore import QPoint, QSize, Qt

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


@pytest.mark.skipif(
    os.environ.get('AZURE', None) is not None, reason="It fails on Azure.")
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
    expected_normal_window_size = (1200, 600)
    expected_normal_window_pos = (mainwindow1.x() + 25, mainwindow1.y() + 25)
    mainwindow1.resize(*expected_normal_window_size)
    mainwindow1.move(*expected_normal_window_pos)

    assert mainwindow1.size() == QSize(*expected_normal_window_size)
    assert mainwindow1.pos() == QPoint(*expected_normal_window_pos)
    assert not mainwindow1.isMaximized()

    # Maximize the window.
    mainwindow1.showMaximized()
    assert mainwindow1.isMaximized()

    # Close the main window.
    assert CONF.get('main', 'window/geometry', None) is None
    mainwindow1.close()
    assert CONF.get('main', 'window/geometry', None) is not None

    # Create a new instance of the main window and assert that the size,
    # position and maximized state were restored from the previous
    # mainwindow that was closed.
    mainwindow2 = MainWindow()
    qtbot.addWidget(mainwindow2)
    mainwindow2.show()
    qtbot.waitForWindowShown(mainwindow2)
    assert mainwindow2.isMaximized()

    # Show window normal size and assert it is the same size and position
    # as that of mainwindow1 instance.
    mainwindow2.setWindowState(Qt.WindowNoState)
    qtbot.wait(1000)
    assert mainwindow2.size() == QSize(*expected_normal_window_size)
    assert mainwindow2.pos() == QPoint(*expected_normal_window_pos)


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


def test_reset_window_layout(mainwindow, qtbot, mocker):
    """
    Test that the option to reset the layout of the mainwindow is
    working as expected.
    """
    mainwindow.data_import_plugin.dockwindow.undock()
    mainwindow.readings_plugin.dockwidget().close()

    assert not mainwindow.data_import_plugin.dockwindow.is_docked()
    assert mainwindow.data_import_plugin.dockwindow.is_visible()
    assert mainwindow.readings_plugin.dockwindow.is_docked()
    assert not mainwindow.readings_plugin.dockwindow.is_visible()

    # Reset layout to default.
    mocker.patch.object(QMessageBox, 'warning', return_value=QMessageBox.Yes)
    mainwindow.reset_window_layout_action.trigger()

    assert mainwindow.data_import_plugin.dockwindow.is_docked()
    assert mainwindow.data_import_plugin.dockwindow.is_visible()
    assert mainwindow.readings_plugin.dockwindow.is_docked()
    assert mainwindow.readings_plugin.dockwindow.is_visible()


# =============================================================================
# ---- Tests show readings
# =============================================================================
def test_view_readings(mainwindow, qtbot):
    """
    Assert that timeseries data tables are created and shown as expected.
    """
    dbmanager = mainwindow.db_connection_manager
    with qtbot.waitSignal(dbmanager.sig_database_connected, timeout=1500):
        mainwindow.databases_plugin.connect_to_database()

    # Switch focus to the table plugin.
    tables_plugin = mainwindow.tables_plugin
    tables_plugin.switch_to_plugin()
    assert tables_plugin.dockwindow.isVisible()

    # Wait until the first row is selected in the table.
    table_obs_well = tables_plugin._tables['table_observation_wells']
    tables_plugin.tabwidget.setCurrentWidget(table_obs_well)
    qtbot.waitUntil(
        lambda: table_obs_well.get_current_obs_well_data() is not None)
    current_obs_well = table_obs_well.get_current_obs_well_data().name
    assert current_obs_well == 0

    # Click on the button to show the readings data for the selected well.
    readings_plugin = mainwindow.readings_plugin
    assert len(readings_plugin._tseries_data_tables) == 0
    qtbot.mouseClick(table_obs_well.show_data_btn, Qt.LeftButton)
    qtbot.waitUntil(lambda: len(readings_plugin._tseries_data_tables) == 1)

    table = readings_plugin._tseries_data_tables[0]
    qtbot.waitUntil(lambda: table.tableview.row_count() == 1826)
    assert table.isVisible()

    # Close the timeseries table.
    readings_plugin.tabwidget.tabCloseRequested.emit(0)
    qtbot.waitUntil(lambda: len(readings_plugin._tseries_data_tables) == 0)


if __name__ == "__main__":
    pytest.main(['-x', os.path.basename(__file__), '-v', '-rw'])
