# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the Repere table.
"""

# ---- Standard imports
from datetime import datetime
import os
from uuid import UUID
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pandas as pd
import pytest
from qtpy.QtWidgets import QMessageBox

# ---- Local imports
from sardes.widgets.tableviews import MSEC_MIN_PROGRESS_DISPLAY


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def tablewidget(mainwindow, qtbot, dbaccessor):
    mainwindow.tables_plugin.switch_to_plugin()
    mainwindow.tables_plugin.tabwidget.setCurrentIndex(4)
    tablewidget = mainwindow.tables_plugin.current_table()

    assert tablewidget.model().name() == 'table_repere'

    # Wait until data are actually charged in the table.
    qtbot.waitUntil(lambda: tablewidget.visible_row_count() > 0)
    qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)

    yield tablewidget
    # The 'tablewidget' is part of the 'mainwindow' and will get
    # destroyed in the 'mainwindow' fixture.


# =============================================================================
# ---- Tests
# =============================================================================
def test_add_repere_data(tablewidget, dbaccessor, qtbot, mocker):
    """
    Test that adding a new repere is working as expected.
    """
    tablemodel = tablewidget.model()
    assert tablewidget.visible_row_count() == 5
    assert len(dbaccessor.get('repere_data')) == 5

    # We add a new row and assert that the UI state is as expected.
    tablewidget.new_row_action.trigger()
    assert tablewidget.visible_row_count() == 6
    assert tablemodel.data_edit_count() == 1
    assert tablewidget.get_data_for_row(5) == [''] * 8
    assert len(dbaccessor.get('repere_data')) == 5
    assert tablemodel.is_new_row_at(tablewidget.current_index())

    # We need to patch the message box that warns the user when
    # a Notnull constraint is violated.
    qmsgbox_patcher = mocker.patch.object(
        QMessageBox, 'exec_', return_value=QMessageBox.Ok)

    # Try to save the changes to the database and assert that a
    # "Notnull constraint violation" message is shown.
    tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 1
    assert tablewidget.visible_row_count() == 6
    assert len(dbaccessor.get('repere_data')) == 5

    # Enter a non null value for the fields 'sampling_feature_uuid',
    # 'top_casing_alt', 'casing_length', 'start_date' and 'is_alt_geodesic'.
    edited_values = {
        'sampling_feature_uuid': UUID('e23753a9-c13d-44ac-9c13-8b7e1278075f'),
        'top_casing_alt': 527.45,
        'casing_length': 3.1,
        'start_date': datetime(2015, 6, 12, 15, 34, 12),
        'is_alt_geodesic': False}
    for colname, edited_value in edited_values.items():
        col = tablemodel.column_names().index(colname)
        model_index = tablemodel.index(5, col)
        tablewidget.model().set_data_edit_at(model_index, edited_value)
    assert tablewidget.get_data_for_row(5) == [
        '09000001', '527.45', '3.1', '524.35',
        '2015-06-12 15:34', '', 'No', '']
    assert tablemodel.data_edit_count() == 6

    # Save the changes to the database.
    with qtbot.waitSignal(tablemodel.sig_data_updated):
        tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 1
    assert tablemodel.data_edit_count() == 0

    repere_data = dbaccessor.get('repere_data')
    assert tablewidget.visible_row_count() == 6
    assert len(repere_data) == 6
    assert repere_data.iloc[5]['sampling_feature_uuid'] == UUID(
        'e23753a9-c13d-44ac-9c13-8b7e1278075f')
    assert repere_data.iloc[5]['top_casing_alt'] == 527.45
    assert repere_data.iloc[5]['casing_length'] == 3.1
    assert repere_data.iloc[5]['start_date'] == datetime(
        2015, 6, 12, 15, 34, 12)
    assert pd.isnull(repere_data.iloc[5]['end_date'])
    assert repere_data.iloc[5]['is_alt_geodesic'] == False


def test_edit_repere_data(tablewidget, qtbot, dbaccessor, obswells_data):
    """
    Test that editing repere data is working as expected.
    """
    tableview = tablewidget.tableview

    edited_values = {
        'sampling_feature_uuid': obswells_data.index[1],
        'top_casing_alt': 10.1,
        'casing_length': 0.7,
        'start_date': datetime(2009, 7, 14),
        'end_date': datetime(2020, 8, 3, 7, 14),
        'is_alt_geodesic': False,
        'repere_note': 'Edited repere note.',
        }

    # Edit each editable field of the first row of the table.
    assert tableview.get_data_for_row(0) == [
        '03037041', '9.3', '1.3', '8.0',
        '2009-07-14 09:00', '2020-08-03 19:14',
        'Yes', 'Repere note #1']
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
        '02200001', '10.1', '0.7', '9.4',
        '2009-07-14 00:00', '2020-08-03 07:14',
        'No', 'Edited repere note.']

    # Save the changes to the database.
    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get('repere_data').iloc[0].to_dict()
    for key in edited_values.keys():
        assert saved_values[key] == edited_values[key]


def test_clear_repere_data(tablewidget, qtbot, dbaccessor):
    """
    Test that clearing sonde data is working as expected.
    """
    tableview = tablewidget.tableview
    clearable_attrs = ['end_date', 'repere_note']

    # Clear each non required field of the first row of the table.
    assert tableview.get_data_for_row(0) == [
        '03037041', '9.3', '1.3', '8.0',
        '2009-07-14 09:00', '2020-08-03 19:14',
        'Yes', 'Repere note #1']
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
        '03037041', '9.3', '1.3', '8.0',
        '2009-07-14 09:00', '', 'Yes', '']

    # Save the changes to the database.
    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get('repere_data').iloc[0].to_dict()
    for attr in clearable_attrs:
        assert pd.isnull(saved_values[attr])


def test_delete_repere_data(tablewidget, qtbot, dbaccessor):
    """
    Test that deleting repere data is working as expected.
    """
    assert tablewidget.visible_row_count() == 5
    assert len(dbaccessor.get('repere_data')) == 5

    # Select and delete the first two rows of the table.
    tablewidget.set_current_index(0, 0)
    tablewidget.select(1, 0)
    assert tablewidget.get_rows_intersecting_selection() == [0, 1]

    tablewidget.delete_row_action.trigger()
    assert tablewidget.model().data_edit_count() == 1

    # Save the changes to the database.
    repere_data = dbaccessor.get('repere_data')
    assert len(repere_data) == 5

    with qtbot.waitSignal(tablewidget.model().sig_data_updated):
        tablewidget.save_edits_action.trigger()

    repere_data = dbaccessor.get('repere_data')
    assert len(repere_data) == 3


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
