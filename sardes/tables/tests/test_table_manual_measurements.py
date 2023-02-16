# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the Manual Measurements table.
"""

# ---- Standard imports
from datetime import datetime
import os
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pandas as pd
import pytest
from qtpy.QtWidgets import QMessageBox

# ---- Local imports
from sardes.utils.data_operations import are_values_equal
from sardes.widgets.tableviews import MSEC_MIN_PROGRESS_DISPLAY


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def tablewidget(mainwindow, qtbot, dbaccessor):
    mainwindow.tables_plugin.switch_to_plugin()
    mainwindow.tables_plugin.tabwidget.setCurrentIndex(2)
    tablewidget = mainwindow.tables_plugin.current_table()

    assert tablewidget.model().name() == 'table_manual_measurements'

    # Wait until data are actually charged in the table.
    qtbot.waitUntil(lambda: tablewidget.visible_row_count() > 0)
    qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)

    yield tablewidget
    # The 'tablewidget' is part of the 'mainwindow' and will get
    # destroyed in the 'mainwindow' fixture.


# =============================================================================
# ---- Tests
# =============================================================================
def test_add_manual_measurements(tablewidget, qtbot, dbaccessor, mocker):
    """
    Test that adding new manual measurements is working as expected.
    """
    tablemodel = tablewidget.model()
    assert tablewidget.visible_row_count() == 6
    assert len(dbaccessor.get('manual_measurements')) == 6

    # We add a new row and assert that the UI state is as expected.
    tablewidget.new_row_action.trigger()
    assert tablewidget.visible_row_count() == 7
    assert len(dbaccessor.get('manual_measurements')) == 6
    assert tablewidget.model().is_new_row_at(tablewidget.current_index())
    assert tablewidget.get_data_for_row(6) == ['', '', '', '']
    assert tablemodel.data_edit_count() == 1

    # We need to patch the message box that warns the user when
    # a Notnull constraint is violated.
    qmsgbox_patcher = mocker.patch.object(
        QMessageBox, 'exec_', return_value=QMessageBox.Ok)

    # Try to save the changes to the database and assert that a
    # "Notnull constraint violation" message is shown.
    tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 1

    # Enter a non null value for the fields 'sampling_feature_uuid', 'datetime'
    # and 'value'.
    obswells = dbaccessor.get('observation_wells_data')
    edited_values = {
        'sampling_feature_uuid': obswells.index[0],
        'datetime': datetime(2012, 3, 2, 16, 15),
        'value': 24.7}
    for colname, edited_value in edited_values.items():
        col = tablemodel.column_names().index(colname)
        model_index = tablemodel.index(6, col)
        tablewidget.model().set_data_edit_at(model_index, edited_value)
    assert tablewidget.get_data_for_row(6) == [
        '03037041', '2012-03-02 16:15:00', '24.7', '']
    assert tablemodel.data_edit_count() == 4

    # Save the changes to the database.
    with qtbot.waitSignal(tablemodel.sig_data_updated):
        tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 1
    assert tablemodel.data_edit_count() == 0

    manual_measurements = dbaccessor.get('manual_measurements')
    assert tablewidget.visible_row_count() == 7
    assert len(manual_measurements) == 7
    for name, value in edited_values.items():
        assert are_values_equal(manual_measurements.iloc[6][name], value)


def test_edit_manual_measurements(tablewidget, qtbot, manual_measurements,
                                  obswells_data, dbaccessor):
    """
    Test that editing manual measurements is working as expected.
    """
    tableview = tablewidget.tableview

    edited_values = {
        'sampling_feature_uuid': obswells_data.index[3],
        'datetime': datetime(2010, 8, 10, 18, 5),
        'value': 5.2,
        'notes': 'edited_measurement_notes'
        }

    # Edit each editable field of the first row of the table.
    assert tableview.get_data_for_row(0) == [
        '03037041', '2010-08-10 16:10:34', '5.23', 'Note first measurement']
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
        '03040002', '2010-08-10 18:05:00', '5.2', 'edited_measurement_notes']

    # Save the changes to the database.
    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get('manual_measurements').iloc[0].to_dict()
    for key in edited_values.keys():
        assert saved_values[key] == edited_values[key]


def test_clear_manual_measurements(tablewidget, qtbot, dbaccessor):
    """
    Test that clearing sonde data is working as expected.
    """
    tableview = tablewidget.tableview
    clearable_attrs = ['notes']

    # Clear each non required field of the first row of the table.
    assert tableview.get_data_for_row(0) == [
        '03037041', '2010-08-10 16:10:34', '5.23', 'Note first measurement']
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
        '03037041', '2010-08-10 16:10:34', '5.23', '']

    # Save the changes to the database.
    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get('manual_measurements').iloc[0].to_dict()
    for attr in clearable_attrs:
        assert pd.isnull(saved_values[attr])


def test_delete_manual_measurements(tablewidget, qtbot, dbaccessor):
    """
    Test that deleting manual measurements is working as expected.
    """
    assert tablewidget.visible_row_count() == 6
    assert len(dbaccessor.get('manual_measurements')) == 6

    # Select and delete the first two rows of the table.
    tablewidget.set_current_index(0, 0)
    tablewidget.select(1, 0)
    assert tablewidget.get_rows_intersecting_selection() == [0, 1]

    tablewidget.delete_row_action.trigger()
    assert tablewidget.model().data_edit_count() == 1

    # Save the changes to the database.
    manual_measurements = dbaccessor.get('manual_measurements')
    assert len(manual_measurements) == 6
    assert manual_measurements.iloc[0]['value'] == 5.23
    assert tablewidget.visible_row_count() == 6

    with qtbot.waitSignal(tablewidget.model().sig_data_updated):
        tablewidget.save_edits_action.trigger()

    manual_measurements = dbaccessor.get('manual_measurements')
    assert len(manual_measurements) == 4
    assert manual_measurements.iloc[0]['value'] == 4.91
    assert tablewidget.visible_row_count() == 4


def test_unique_constraint(tablewidget, qtbot, mocker, dbaccessor):
    """
    Test that unique constraint violations are reported as expected.
    """
    tablemodel = tablewidget.model()

    # We need to patch the message box that appears to warn user when
    # a unique constraint is violated.
    qmsgbox_patcher = mocker.patch.object(
        QMessageBox, 'exec_', return_value=QMessageBox.Ok)

    # Set the station of the fourth as that of the first row.
    col = tablemodel.column_names().index('sampling_feature_uuid')
    orig_value = tablemodel.get_value_at(tablemodel.index(3, col))
    tablewidget.model().set_data_edit_at(
        tablemodel.index(3, col),
        tablemodel.get_value_at(tablemodel.index(0, col)))
    assert tablemodel.is_data_edited_at(tablemodel.index(3, col))
    assert tablemodel.data_edit_count() == 1

    # Save the changes to the database.
    with qtbot.waitSignal(tablemodel.sig_data_updated):
        tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 0
    assert not tablemodel.is_data_edited_at(tablemodel.index(3, col))
    assert tablemodel.data_edit_count() == 0

    # Set the datetime of the fourth row as that of the first row.
    col = tablemodel.column_names().index('datetime')
    tablewidget.model().set_data_edit_at(
        tablemodel.index(3, col),
        tablemodel.get_value_at(tablemodel.index(0, col)))
    assert tablemodel.is_data_edited_at(tablemodel.index(3, col))
    assert tablemodel.data_edit_count() == 1

    # Try to save the changes to the database and assert that a
    # "Unique constraint violation" message is shown as expected.
    tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 1

    # Change back the station of the fourth row to its original value and
    # save the results to the database.
    col = tablemodel.column_names().index('sampling_feature_uuid')
    tablewidget.model().set_data_edit_at(tablemodel.index(3, col), orig_value)
    assert tablemodel.is_data_edited_at(tablemodel.index(3, col))
    assert tablemodel.data_edit_count() == 2

    # Save the changes to the database.
    with qtbot.waitSignal(tablemodel.sig_data_updated):
        tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 1
    assert tablemodel.data_edit_count() == 0


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
