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
import os.path as osp
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pytest
from qtpy.QtCore import QPoint, QSize, Qt

# ---- Local imports
from sardes.config.gui import INIT_MAINWINDOW_SIZE
from sardes.config.main import CONF
from sardes.app.mainwindow import MainWindow, QMessageBox
from sardes.app.capture import SysCaptureManager
from sardes.database.accessors import DatabaseAccessorSardesLite


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def database(tmp_path, database_filler):
    database = osp.join(tmp_path, 'sqlite_database_test.db')
    dbaccessor = DatabaseAccessorSardesLite(database)
    dbaccessor.init_database()
    database_filler(dbaccessor)
    dbaccessor.close_connection()
    return database


@pytest.fixture
def mainwindow(qtbot, mocker):
    """A fixture for Sardes main window."""
    mainwindow = MainWindow()
    mainwindow.show()
    qtbot.waitExposed(mainwindow)

    # We need to wait for the mainwindow to be initialized correctly.
    qtbot.wait(150)
    yield mainwindow

    # We need to wait for the mainwindow to close properly to avoid
    # runtime errors on the c++ side.
    with qtbot.waitSignal(mainwindow.sig_about_to_close):
        mainwindow.close()

    # Make sure all plugins dockwindow are closed.
    for plugin in mainwindow.internal_plugins:
        if plugin.dockwindow is not None:
            assert not plugin.dockwindow.isVisible()


# =============================================================================
# ---- Tests for MainWindow
# =============================================================================
def test_mainwindow_init(mainwindow):
    """Test that the main window is initialized correctly."""
    assert mainwindow


def test_sardes_console(qtbot, mocker):
    """
    Test that sardes console is initialized properly in the mainwindow.
    """
    sys_capture_manager = SysCaptureManager()

    mainwindow = MainWindow(sys_capture_manager=sys_capture_manager)
    mainwindow.show()
    qtbot.waitExposed(mainwindow)

    # Assert that the console to show stantart Python interpreter output was
    # installed as expected in the MainWindow.
    assert mainwindow.console is not None
    assert not mainwindow.console.isVisible()
    mainwindow.console_action.trigger()
    assert mainwindow.console.isVisible()

    # Assert that the console is printing Python interpreter output
    # as expected.
    assert mainwindow.console.plain_text() == ''
    sys_capture_manager.stdout_emitter.sig_new_text.emit(
        'stdout_test_message\n')
    sys_capture_manager.stderr_emitter.sig_new_text.emit(
        'stderr_test_message')
    assert mainwindow.console.plain_text() == (
        'stdout_test_message\nstderr_test_message')

    # Assert that the sardes console is closed with the main window.
    with qtbot.waitSignal(mainwindow.sig_about_to_close):
        mainwindow.close()
    assert not mainwindow.console.isVisible()


@pytest.mark.skipif(
    os.environ.get('AZURE', None) is not None, reason="It fails on Azure.")
def test_mainwindow_settings(qtbot, mocker):
    """
    Test that the window size and position are store and restore correctly
    in and from our configs.
    """
    CONF.set('main', 'window/geometry', None)

    mainwindow1 = MainWindow()
    mainwindow1.show()
    qtbot.waitExposed(mainwindow1)

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
    with qtbot.waitSignal(mainwindow1.sig_about_to_close):
        mainwindow1.close()
    assert CONF.get('main', 'window/geometry', None) is not None

    # Create a new instance of the main window and assert that the size,
    # position and maximized state were restored from the previous
    # mainwindow that was closed.
    mainwindow2 = MainWindow()
    mainwindow2.show()
    qtbot.waitExposed(mainwindow2)
    assert mainwindow2.isMaximized()

    # Show window normal size and assert it is the same size and position
    # as that of mainwindow1 instance.
    mainwindow2.setWindowState(Qt.WindowNoState)
    qtbot.wait(1000)
    assert mainwindow2.size() == QSize(*expected_normal_window_size)
    assert mainwindow2.pos() == QPoint(*expected_normal_window_pos)

    # Close the second mainwindow.
    with qtbot.waitSignal(mainwindow2.sig_about_to_close):
        mainwindow2.close()


def test_mainwindow_lang_change(qtbot, mocker):
    """
    Test that the window size and position are store and restore correctly
    in and from our configs.
    """
    mainwindow = MainWindow()
    mainwindow.show()
    qtbot.waitExposed(mainwindow)

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
    with qtbot.waitSignal(mainwindow.sig_about_to_close):
        mainwindow.close()

    # Create a new instance of the main window and assert that the
    # language was changed for Français.
    mainwindow_restart = MainWindow()
    mainwindow_restart.show()
    qtbot.waitExposed(mainwindow_restart)

    lang_actions = mainwindow_restart.lang_menu.actions()
    checked_actions = [act for act in lang_actions if act.isChecked()]
    assert len(checked_actions) == 1
    assert checked_actions[0].text() == 'Français'

    # Close the second mainwindow.
    with qtbot.waitSignal(mainwindow_restart.sig_about_to_close):
        mainwindow_restart.close()


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


def test_view_readings(mainwindow, qtbot, database, readings_data,
                       obswells_data):
    """
    Assert that timeseries data tables are created and shown as expected.
    """
    # Set the path to the demo database in the Sardes SQlite database dialog.
    dbconn_widget = mainwindow.databases_plugin.db_connection_widget
    assert dbconn_widget.dbtype_combobox.currentText() == 'Sardes SQLite'

    dbialog = dbconn_widget.get_current_database_dialog()
    dbialog.dbname_widget.set_path(database)

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
    assert current_obs_well == obswells_data.index[0]

    # Click on the button to show the readings data for the selected well.
    readings_plugin = mainwindow.readings_plugin
    assert len(readings_plugin._tseries_table_widgets) == 0

    qtbot.mouseClick(table_obs_well.show_data_btn, Qt.LeftButton)
    qtbot.waitUntil(lambda: len(readings_plugin._tseries_table_widgets) == 1)

    table = readings_plugin._tseries_table_widgets[obswells_data.index[0]]
    qtbot.waitUntil(lambda: table.tableview.row_count() == len(readings_data))
    assert table.isVisible()

    # Close the timeseries table.
    readings_plugin.tabwidget.tabCloseRequested.emit(0)
    qtbot.waitUntil(lambda: len(readings_plugin._tseries_table_widgets) == 0)


def test_close_plugins_when_undocked(mainwindow, qtbot):
    """
    Test that each plugins are closed correctly when they are undocked.
    """
    count = 0
    for plugin in mainwindow.internal_plugins:
        if plugin.dockwindow is not None:
            count += 1
            assert plugin.dockwindow.is_docked()
            plugin.dockwindow.undock()
            assert not plugin.dockwindow.is_docked()
    assert count > 0

    # The assertion that each plugin's dockwindow is closed alonside
    # the mainwindow is done in the mainwindow fixture deconstruction,
    # so we do not need to assert this here.


def test_restart_plugins_when_undocked(mainwindow, qtbot):
    """
    Test that each plugin are reinitialized correctly in an undocked state
    as per the previous test and test that docking the plugin back in the
    mainwindow is working as expected.
    """
    count = 0
    for plugin in mainwindow.internal_plugins:
        if plugin.dockwindow is not None:
            count += 1
            assert not plugin.dockwindow.is_docked()
            assert plugin.dockwindow.isVisible()

            # Dock the plugin back in the mainwindow.
            plugin.dockwindow.dock()
            assert plugin.dockwindow.is_docked()
            assert plugin.dockwindow.isVisible()
    assert count > 0


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
