# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the Observation Wells table.
"""

# ---- Standard imports
import os
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import numpy as np
import pandas as pd
import pytest
from qtpy.QtCore import QUrl, QPoint
from qtpy.QtGui import QDesktopServices
from qtpy.QtWidgets import QFileDialog, QMessageBox

# ---- Local imports
from sardes.api.timeseries import DataType
from sardes.widgets.tableviews import MSEC_MIN_PROGRESS_DISPLAY
from sardes.database.accessors.accessor_helpers import init_tseries_dels


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def tablewidget(mainwindow, qtbot, dbaccessor):
    mainwindow.tables_plugin.switch_to_plugin()
    mainwindow.tables_plugin.tabwidget.setCurrentIndex(0)
    tablewidget = mainwindow.tables_plugin.current_table()

    assert tablewidget.model().name() == 'table_observation_wells'

    # Wait until data are actually charged in the table.
    qtbot.waitUntil(lambda: tablewidget.visible_row_count() > 0)
    qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)

    yield tablewidget
    # The 'tablewidget' is part of the 'mainwindow' and will get
    # destroyed in the 'mainwindow' fixture.


# =============================================================================
# ---- Tests
# =============================================================================
def test_show_in_google_maps(tablewidget, qtbot, mocker):
    """
    Test that the tool to show the currently selected well in Google maps is
    working as expected.
    """
    tableview = tablewidget.tableview

    # We are selecting the first well in the table.
    tableview.set_current_index(0, 0)

    # We are patching QDesktopServices.openUrl because we don't want to
    # slow down tests by opening web pages on an external browser.
    patcher_qdesktopservices = mocker.patch.object(
        QDesktopServices, 'openUrl', return_value=True)
    tablewidget.show_in_google_maps()
    patcher_qdesktopservices.assert_called_once_with(QUrl(
        'https://www.google.com/maps/search/?api=1&query=45.445178,-72.828773'
        ))


def test_construction_log_tool(tablewidget, constructlog, qtbot, mocker):
    """
    Test that the tool to add, show and delete construction logs
    is working as expected.
    """
    tablemodel = tablewidget.model()
    constructlogs_manager = tablewidget.construction_logs_manager

    # Check that the number of file attachment is as expected. There is
    # supposed to be 2 files for the first 4 wells of the test database:
    # one construction log and one water quality file.
    assert len(tablemodel.libraries['attachments_info']) == 4

    # Select the last row of the table, which corresponds to well '09000001'.
    # This well does not have any attachment or monitoring data.
    tablewidget.set_current_index(4, 0)
    assert tablewidget.current_data() == '09000001'

    # Make sure the state of the construction log menu is as expected.
    # Note that we need to show the menu to trigger an update of its state.
    pos = constructlogs_manager.toolbutton.mapToGlobal(QPoint(0, 0))
    constructlogs_manager.toolbutton.menu().popup(pos)
    assert constructlogs_manager.attach_action.isEnabled()
    assert not constructlogs_manager.show_action.isEnabled()
    assert not constructlogs_manager.remove_action.isEnabled()

    # Attach a construction log to well '09000001'.
    mocker.patch.object(
        QFileDialog, 'getOpenFileName', return_value=(constructlog, None))
    with qtbot.waitSignal(constructlogs_manager.sig_attachment_added):
        constructlogs_manager.attach_action.trigger()
    qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)
    assert len(tablemodel.libraries['attachments_info']) == 4 + 1

    pos = constructlogs_manager.toolbutton.mapToGlobal(QPoint(0, 0))
    constructlogs_manager.toolbutton.menu().popup(pos)
    assert constructlogs_manager.attach_action.isEnabled()
    assert constructlogs_manager.show_action.isEnabled()
    assert constructlogs_manager.remove_action.isEnabled()

    # Show the newly added construction log in an external application.
    mocker.patch('os.startfile')
    with qtbot.waitSignal(constructlogs_manager.sig_attachment_shown):
        constructlogs_manager.show_action.trigger()

    # Delete the newly added construction log from the database.
    with qtbot.waitSignal(constructlogs_manager.sig_attachment_removed):
        constructlogs_manager.remove_action.trigger()
    qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)
    assert len(tablemodel.libraries['attachments_info']) == 4

    pos = constructlogs_manager.toolbutton.mapToGlobal(QPoint(0, 0))
    constructlogs_manager.toolbutton.menu().popup(pos)
    assert constructlogs_manager.attach_action.isEnabled()
    assert not constructlogs_manager.show_action.isEnabled()
    assert not constructlogs_manager.remove_action.isEnabled()
    constructlogs_manager.toolbutton.menu().close()


def test_select_observation_well(tablewidget, qtbot):
    """
    Test that selecting an observation well is working as expected.
    """
    tableview = tablewidget.tableview

    # We select the first monitoring station in the table and we assert that
    # the UI state is as expected.
    tableview.set_current_index(0, 0)

    assert not tablewidget.model().is_new_row_at(tableview.current_index())
    assert tablewidget.show_data_btn.isEnabled()
    assert tablewidget.show_gmap_btn.isEnabled()
    assert tablewidget.construction_logs_manager.isEnabled()
    assert tablewidget.water_quality_report_tool.isEnabled()

    # We select other monitoring stations and we assert that
    # the UI state is as expected.
    tableview.set_current_index(1, 0)
    assert not tablewidget.water_quality_report_tool.isEnabled()

    tableview.set_current_index(2, 0)
    assert tablewidget.water_quality_report_tool.isEnabled()


def test_add_observation_well(tablewidget, qtbot, dbaccessor, mocker):
    """
    Test that adding a new observation well is working as expected.
    """
    tablemodel = tablewidget.model()
    assert tablewidget.visible_row_count() == 5
    assert len(dbaccessor.get('observation_wells_data')) == 5

    # We add a new row and assert that the UI state is as expected.
    tablewidget.new_row_action.trigger()
    assert tablewidget.visible_row_count() == 6
    assert tablemodel.data_edit_count() == 1
    assert tablewidget.get_data_for_row(5) == [''] * 15
    assert len(dbaccessor.get('observation_wells_data')) == 5

    assert tablemodel.is_new_row_at(tablewidget.current_index())
    assert not tablewidget.show_data_btn.isEnabled()
    assert not tablewidget.construction_logs_manager.isEnabled()
    assert not tablewidget.water_quality_report_tool.isEnabled()

    # We need to patch the message box that warns the user when
    # a Notnull constraint is violated.
    qmsgbox_patcher = mocker.patch.object(
        QMessageBox, 'exec_', return_value=QMessageBox.Ok)

    # Try to save the changes to the database and assert that a
    # "Notnull constraint violation" message is shown.
    tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 1
    assert tablewidget.visible_row_count() == 6
    assert len(dbaccessor.get('observation_wells_data')) == 5

    # Enter a non null value for the fields 'obs_well_id' and
    # 'is_station_active'.
    edited_values = {
        'obs_well_id': 'new_well_id',
        'is_station_active': True}
    for colname, edited_value in edited_values.items():
        col = tablemodel.column_names().index(colname)
        model_index = tablemodel.index(5, col)
        tablewidget.model().set_data_edit_at(model_index, edited_value)
    assert tablewidget.get_data_for_row(5)[0] == 'new_well_id'
    assert tablewidget.get_data_for_row(5)[-2] == 'Yes'
    assert tablemodel.data_edit_count() == 3

    # Save the changes to the database.
    with qtbot.waitSignal(tablemodel.sig_data_updated):
        tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 1
    assert tablemodel.data_edit_count() == 0

    obswells = dbaccessor.get('observation_wells_data')
    assert tablewidget.visible_row_count() == 6
    assert len(obswells) == 6
    assert obswells.iloc[5]['obs_well_id'] == 'new_well_id'
    assert obswells.iloc[5]['is_station_active'] == True


def test_edit_observation_well(tablewidget, qtbot, obswells_data, dbaccessor):
    """
    Test that editing observation well data is working as expected.
    """
    tableview = tablewidget.tableview

    edited_values = {
        'obs_well_id': 'edited_obs_well_id',
        'municipality': 'edited_municipality',
        'common_name': 'edited_common_name',
        'latitude': 42.424242,
        'longitude': -65.656565,
        'aquifer_type': 'edited_aquifer_type',
        'confinement': 'edited_confinement',
        'aquifer_code': 999,
        'in_recharge_zone': 2,
        'is_influenced': 2,
        'is_station_active': False,
        'obs_well_notes': 'edited_obs_well_notes'
        }

    wlvl = dbaccessor.get_timeseries_for_obs_well(
        obswells_data.index[0], [DataType.WaterLevel])[DataType.WaterLevel]

    # Edit each editable field of the first row of the table.
    assert tableview.get_data_for_row(0) == [
        '03037041', "St-Paul-d'Abbotsford", "Saint-Paul-d'Abbotsford",
        'MT', '3', 'Confined', 'No', 'No', '45.445178', '-72.828773',
        '2015-01-01', '2020-12-31', str(np.round(np.mean(wlvl), 3)),
        'Yes', 'Note for well 03037041']
    for col in range(tableview.visible_column_count()):

        current_index = tableview.set_current_index(0, col)
        if not tableview.is_data_editable_at(current_index):
            continue

        orig_value = tableview.model().get_value_at(current_index)
        edit_value = edited_values[tableview.visible_columns()[col]]
        assert orig_value != edit_value

        assert not tableview.model().is_data_edited_at(current_index)
        tableview.edit(current_index)
        item_delegate = tableview.itemDelegate(tableview.current_index())
        item_delegate.set_editor_data(edit_value)
        item_delegate.commit_data()
        assert tableview.model().is_data_edited_at(current_index)
        assert tableview.model().get_value_at(current_index) == edit_value
    assert tableview.get_data_for_row(0) == [
        'edited_obs_well_id', 'edited_common_name', 'edited_municipality',
        'edited_aquifer_type', '999', 'edited_confinement',
        'NA', 'NA', '42.424242', '-65.656565', '2015-01-01', '2020-12-31',
        str(np.round(np.mean(wlvl), 3)), 'No', 'edited_obs_well_notes']

    # Save the changes to the database.
    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get('observation_wells_data').iloc[0].to_dict()
    for key in edited_values.keys():
        assert saved_values[key] == edited_values[key]


def test_clear_observation_well(tablewidget, qtbot, dbaccessor, obswells_data):
    """
    Test that clearing observation well data is working as expected.
    """
    tableview = tablewidget.tableview
    clearable_attrs = [
        'municipality', 'common_name', 'latitude', 'longitude',
        'aquifer_type', 'confinement', 'aquifer_code', 'in_recharge_zone',
        'is_influenced', 'obs_well_notes'
        ]

    wlvl = dbaccessor.get_timeseries_for_obs_well(
        obswells_data.index[0], [DataType.WaterLevel])[DataType.WaterLevel]

    # Clear each non required field of the first row of the table.
    assert tableview.get_data_for_row(0) == [
        '03037041', "St-Paul-d'Abbotsford", "Saint-Paul-d'Abbotsford",
        'MT', '3', 'Confined', 'No', 'No', '45.445178', '-72.828773',
        '2015-01-01', '2020-12-31', str(np.round(np.mean(wlvl), 3)),
        'Yes', 'Note for well 03037041']
    for col in range(tableview.visible_column_count()):
        current_index = tableview.set_current_index(0, col)
        column = tableview.visible_columns()[col]
        if not tableview.is_data_clearable_at(current_index):
            assert column not in clearable_attrs
        else:
            assert column in clearable_attrs

            assert not tableview.model().is_data_edited_at(current_index)
            assert not tableview.model().is_null(current_index)
            tableview.clear_item_action.trigger()
            assert tableview.model().is_data_edited_at(current_index)
            assert tableview.model().is_null(current_index)
    assert tableview.get_data_for_row(0) == [
        '03037041', '', '', '', '', '', '', '', '', '',
        '2015-01-01', '2020-12-31', str(np.round(np.mean(wlvl), 3)), 'Yes', '']

    # Save the changes to the database.
    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get('observation_wells_data').iloc[0].to_dict()
    for attr in clearable_attrs:
        assert pd.isnull(saved_values[attr])


def test_delete_observation_well(tablewidget, qtbot, dbaccessor, mocker,
                                 dbconnmanager):
    """
    Test that deleting observation wells is working as expected.
    """
    assert tablewidget.visible_row_count() == 5
    assert len(dbaccessor.get('observation_wells_data')) == 5

    # Delete the first row of the table.
    tablewidget.set_current_index(0, 0)
    assert tablewidget.current_data() == '03037041'

    tablewidget.delete_row_action.trigger()
    assert len(tablewidget.model().tabledata().deleted_rows()) == 1
    assert tablewidget.model().data_edit_count() == 1
    assert tablewidget.visible_row_count() == 5
    assert len(dbaccessor.get('observation_wells_data')) == 5

    # Try to save the changes to the database. A foreign constraint error
    # message should appear.
    qmsgbox_patcher = mocker.patch.object(
        QMessageBox, 'exec_', return_value=QMessageBox.Ok)

    tablewidget.save_edits_action.trigger()
    qtbot.waitUntil(lambda: qmsgbox_patcher.call_count == 1)

    # Delete the timeseries associated with station '03037041' and try again.
    obswell_id = tablewidget.model().dataf.index[0]
    readings = dbaccessor.get_timeseries_for_obs_well(obswell_id)
    data_types = [DataType.WaterLevel, DataType.WaterTemp, DataType.WaterEC]
    tseries_dels = init_tseries_dels()
    for data_type in data_types:
        to_delete = readings[
            [data_type, 'datetime', 'obs_id']].dropna(subset=[data_type])
        to_delete['data_type'] = data_type
        to_delete = to_delete.drop(labels=data_type, axis=1)
        tseries_dels = tseries_dels.append(
            to_delete, ignore_index=True)

    with qtbot.waitSignal(dbconnmanager.sig_run_tasks_finished, timeout=5000):
        dbconnmanager.delete_timeseries_data(tseries_dels, obswell_id)
    assert dbaccessor.get_timeseries_for_obs_well(obswell_id).empty

    tablewidget.save_edits_action.trigger()
    qtbot.waitUntil(lambda: qmsgbox_patcher.call_count == 2)

    # Delete the manual measurements and try again.
    with qtbot.waitSignal(dbconnmanager.sig_run_tasks_finished, timeout=5000):
        dbconnmanager.delete(
            'manual_measurements',
            dbaccessor.get('manual_measurements').index[:3])

    tablewidget.save_edits_action.trigger()
    qtbot.waitUntil(lambda: qmsgbox_patcher.call_count == 3)

    # Delete the repere data and try again.
    with qtbot.waitSignal(dbconnmanager.sig_run_tasks_finished, timeout=5000):
        dbconnmanager.delete(
            'repere_data',
            dbaccessor.get('repere_data').index[0])

    tablewidget.save_edits_action.trigger()
    qtbot.waitUntil(lambda: qmsgbox_patcher.call_count == 4)

    # Delete the remark data and try again.
    with qtbot.waitSignal(dbconnmanager.sig_run_tasks_finished, timeout=5000):
        dbconnmanager.delete(
            'remarks',
            dbaccessor.get('remarks').index[0])

    tablewidget.save_edits_action.trigger()
    qtbot.waitUntil(lambda: qmsgbox_patcher.call_count == 5)

    # Delete the sonde installations and try again (now it should work).
    with qtbot.waitSignal(dbconnmanager.sig_run_tasks_finished, timeout=5000):
        dbconnmanager.delete(
            'sonde_installations',
            dbaccessor.get('sonde_installations').index[0])

    assert tablewidget.visible_row_count() == 5
    assert len(dbaccessor.get('observation_wells_data')) == 5

    with qtbot.waitSignal(tablewidget.model().sig_data_updated):
        tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 5

    assert tablewidget.visible_row_count() == 4
    assert len(dbaccessor.get('observation_wells_data')) == 4


def test_unique_constraint(tablewidget, qtbot, mocker, dbaccessor):
    """
    Test that unique constraint violations are reported as expected.
    """
    tablemodel = tablewidget.model()

    # We need to patch the message box that appears to warn user when
    # a unique constraint is violated.
    qmsgbox_patcher = mocker.patch.object(
        QMessageBox, 'exec_', return_value=QMessageBox.Ok)

    # Set the station id of the second row as that of the first row.
    model_index = tablemodel.index(1, 0)
    tablemodel.set_data_edit_at(model_index, '03037041')
    assert tablemodel.is_data_edited_at(model_index)
    assert tablemodel.data_edit_count() == 1

    # Try to save the changes to the database and assert that a
    # "Unique constraint violation" message is shown as expected.
    tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 1


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
