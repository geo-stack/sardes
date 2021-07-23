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
from datetime import datetime, date
import os
import os.path as osp
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pandas as pd
import pytest

# ---- Local imports
from sardes.widgets.tableviews import MSEC_MIN_PROGRESS_DISPLAY


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def tablewidget(mainwindow, qtbot, dbaccessor, manual_measurements):
    # Select the tab corresponding to the observation wells table.
    tablewidget = mainwindow.plugin._tables['table_manual_measurements']
    mainwindow.plugin.tabwidget.setCurrentWidget(tablewidget)
    tableview = tablewidget.tableview
    qtbot.waitUntil(
        lambda: tableview.visible_row_count() == len(manual_measurements))
    qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)

    assert tableview.row_count() == len(manual_measurements)
    assert tableview.column_count() == len(manual_measurements.columns)

    yield tablewidget

    # We need to wait for the mainwindow to close properly to avoid
    # runtime errors on the c++ side.
    with qtbot.waitSignal(mainwindow.sig_about_to_close):
        mainwindow.close()


# =============================================================================
# ---- Tests
# =============================================================================
def test_add_manual_measurements(tablewidget, qtbot, manual_measurements,
                                 dbaccessor):
    """
    Test that adding new manual measurements is working as expected.
    """
    tableview = tablewidget.tableview

    # We add a new row and assert that the UI state is as expected.
    new_row = len(manual_measurements)
    assert tableview.visible_row_count() == len(manual_measurements)
    tableview.new_row_action.trigger()
    assert tableview.visible_row_count() == len(manual_measurements) + 1
    assert tableview.model().is_new_row_at(tableview.current_index())
    assert tableview.get_data_for_row(new_row) == ['', '', '', '']

    # Save the changes to the database.
    saved_values = dbaccessor.get_manual_measurements()
    assert len(saved_values) == len(manual_measurements)

    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get_manual_measurements()
    assert len(saved_values) == len(manual_measurements) + 1


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
        '03037041', '2010-08-10 16:10', '5.23', 'Note for first measurement']
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
        '03040002', '2010-08-10 18:05', '5.2', 'edited_measurement_notes']

    # Save the changes to the database.
    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get_manual_measurements().iloc[0].to_dict()
    for key in edited_values.keys():
        assert saved_values[key] == edited_values[key]


def test_clear_manual_measurements(tablewidget, qtbot, dbaccessor):
    """
    Test that clearing sonde data is working as expected.
    """
    tableview = tablewidget.tableview
    clearable_attrs = [
        'sampling_feature_uuid', 'datetime', 'value', 'notes']

    # Clear each non required field of the first row of the table.
    assert tableview.get_data_for_row(0) == [
        '03037041', '2010-08-10 16:10', '5.23', 'Note for first measurement']
    for col in range(tableview.visible_column_count()):
        current_index = tableview.set_current_index(0, col)
        column = tableview.visible_columns()[col]
        if tableview.is_data_required_at(current_index):
            assert column not in clearable_attrs
        else:
            assert column in clearable_attrs

            assert not tableview.model().is_data_edited_at(current_index)
            assert not tableview.model().is_null(current_index)
            tableview.clear_item_action.trigger()
            assert tableview.model().is_data_edited_at(current_index)
            assert tableview.model().is_null(current_index)
    assert tableview.get_data_for_row(0) == ['', '', '', '']

    # Save the changes to the database.
    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get_manual_measurements().iloc[0].to_dict()
    for attr in clearable_attrs:
        assert pd.isnull(saved_values[attr])


def test_delete_manual_measurements(tablewidget, qtbot, manual_measurements,
                                    obswells_data, dbaccessor):
    """
    Test that deleting manual measurements is working as expected.
    """
    tableview = tablewidget.tableview

    # Select and delete the first two rows of the table.
    tableview.set_current_index(0, 0)
    tableview.select(1, 0)
    assert tableview.get_rows_intersecting_selection() == [0, 1]

    tableview.delete_row_action.trigger()
    assert tableview.model().data_edit_count() == 1

    # Save the changes to the database.
    saved_values = dbaccessor.get_manual_measurements()
    assert len(saved_values) == len(manual_measurements)
    assert saved_values.iloc[0]['value'] == 5.23

    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get_manual_measurements()
    assert len(saved_values) == len(manual_measurements) - 2
    assert saved_values.iloc[0]['value'] == 4.91


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
