# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the Sonde Installations table.
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
    mainwindow.tables_plugin.tabwidget.setCurrentIndex(3)
    tablewidget = mainwindow.tables_plugin.current_table()

    assert tablewidget.model().name() == 'table_sonde_installations'

    # Wait until data are actually charged in the table.
    qtbot.waitUntil(lambda: tablewidget.visible_row_count() > 0)
    qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)

    yield tablewidget
    # The 'tablewidget' is part of the 'mainwindow' and will get
    # destroyed in the 'mainwindow' fixture.


# =============================================================================
# ---- Tests
# =============================================================================
def test_add_sonde_installations(tablewidget, dbaccessor, qtbot, mocker):
    """
    Test that adding new sonde installations is working as expected.
    """
    tablemodel = tablewidget.model()
    assert tablewidget.visible_row_count() == 6
    assert len(dbaccessor.get('sonde_installations')) == 6

    # We add a new row and assert that the UI state is as expected.
    tablewidget.new_row_action.trigger()
    assert tablewidget.visible_row_count() == 7
    assert tablemodel.data_edit_count() == 1
    assert tablewidget.get_data_for_row(6) == [''] * 6
    assert tablemodel.is_new_row_at(tablewidget.current_index())
    assert len(dbaccessor.get('sonde_installations')) == 6

    # We need to patch the message box that warns the user when
    # a Notnull constraint is violated.
    qmsgbox_patcher = mocker.patch.object(
        QMessageBox, 'exec_', return_value=QMessageBox.Ok)

    # Try to save the changes to the database and assert that a
    # "Notnull constraint violation" message is shown.
    tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 1
    assert tablewidget.visible_row_count() == 7
    assert len(dbaccessor.get('sonde_installations')) == 6

    # Enter a non null value for the fields 'sampling_feature_uuid',
    # 'sonde_uuid', 'start_date', and 'install_depth'.
    edited_values = {
        'sampling_feature_uuid': UUID('e23753a9-c13d-44ac-9c13-8b7e1278075f'),
        'sonde_uuid': UUID('3b8f4a6b-14d0-461e-8f1a-08a5ea465a1e'),
        'start_date': datetime(2015, 6, 12, 15, 34, 12),
        'install_depth': 12.23}
    for colname, edited_value in edited_values.items():
        col = tablemodel.column_names().index(colname)
        model_index = tablemodel.index(6, col)
        tablewidget.model().set_data_edit_at(model_index, edited_value)
    assert tablewidget.get_data_for_row(6) == [
        '09000001', '1016042 - Solinst Barologger M1.5', '2015-06-12 15:34',
        '', '12.23', '']
    assert tablemodel.data_edit_count() == 5

    # Save the changes to the database.
    with qtbot.waitSignal(tablemodel.sig_data_updated):
        tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 1
    assert tablemodel.data_edit_count() == 0

    sonde_installations = dbaccessor.get('sonde_installations')
    assert tablewidget.visible_row_count() == 7
    assert len(sonde_installations) == 7
    assert sonde_installations.iloc[6]['sampling_feature_uuid'] == UUID(
        'e23753a9-c13d-44ac-9c13-8b7e1278075f')
    assert sonde_installations.iloc[6]['sonde_uuid'] == UUID(
        '3b8f4a6b-14d0-461e-8f1a-08a5ea465a1e')
    assert sonde_installations.iloc[6]['start_date'] == datetime(
        2015, 6, 12, 15, 34, 12)
    assert sonde_installations.iloc[6]['install_depth'] == 12.23


def test_edit_sonde_installations(tablewidget, qtbot, sondes_installation,
                                  obswells_data, sondes_data, dbaccessor):
    """
    Test that editing sonde installations is working as expected.
    """
    tableview = tablewidget.tableview

    edited_values = {
        'sampling_feature_uuid': obswells_data.index[3],
        'sonde_uuid': sondes_data.index[3],
        'start_date': datetime(2010, 8, 1, 12, 0),
        'end_date': datetime(2010, 8, 30, 19, 16),
        'install_depth': 6.34,
        'install_note': 'Edited sonde install note.'
        }

    # Edit each editable field of the first row of the table.
    assert tableview.get_data_for_row(0) == [
        '03037041', '1016042 - Solinst Barologger M1.5',
        '2006-08-24 18:00', '2020-12-31 07:14', '9.02',
        'Note for first sonde installation.']
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
        '03040002', '1016387 - Solinst LT M10 Gold',
        '2010-08-01 12:00', '2010-08-30 19:16', '6.34',
        'Edited sonde install note.']

    # Save the changes to the database.
    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get('sonde_installations').iloc[0].to_dict()
    for key in edited_values.keys():
        assert saved_values[key] == edited_values[key], key


def test_clear_sonde_installations(tablewidget, qtbot, dbaccessor):
    """
    Test that clearing sonde installations is working as expected.
    """
    tableview = tablewidget.tableview
    clearable_attrs = ['end_date', 'install_note']

    # Clear each non required field of the first row of the table.
    assert tableview.get_data_for_row(0) == [
        '03037041', '1016042 - Solinst Barologger M1.5',
        '2006-08-24 18:00', '2020-12-31 07:14', '9.02',
        'Note for first sonde installation.']
    for col in range(tableview.visible_column_count()):
        current_index = tableview.set_current_index(0, col)
        column = tableview.visible_columns()[col]
        if not tableview.is_data_clearable_at(current_index):
            assert column not in clearable_attrs, column
        else:
            assert column in clearable_attrs, column

            assert not tableview.model().is_data_edited_at(current_index)
            assert not tableview.model().is_null(current_index)
            tableview.clear_item_action.trigger()
            assert tableview.model().is_data_edited_at(current_index)
            assert tableview.model().is_null(current_index)
    assert tableview.get_data_for_row(0) == [
        '03037041', '1016042 - Solinst Barologger M1.5',
        '2006-08-24 18:00', '', '9.02', '']

    # Save the changes to the database.
    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get('sonde_installations').iloc[0].to_dict()
    for attr in clearable_attrs:
        assert pd.isnull(saved_values[attr])


def test_delete_sonde_installations(tablewidget, qtbot, dbaccessor, mocker):
    """
    Test that deleting sonde installations is working as expected.
    """
    assert tablewidget.visible_row_count() == 6
    assert len(dbaccessor.get('sonde_installations')) == 6

    # We need to patch the message box that appears to warn users about
    # what happens with the associated monitoring data when deleting a
    # sonde installation from the database.
    qmsgbox_patcher = mocker.patch.object(
        QMessageBox, 'exec_', return_value=QMessageBox.Ok)

    # Select and delete the first two rows of the table.
    tablewidget.set_current_index(0, 0)
    tablewidget.select(1, 0)
    assert tablewidget.get_rows_intersecting_selection() == [0, 1]

    tablewidget.delete_row_action.trigger()
    assert tablewidget.model().data_edit_count() == 1
    assert qmsgbox_patcher.call_count == 1

    # Save the changes to the database.
    assert tablewidget.visible_row_count() == 6
    assert len(dbaccessor.get('sonde_installations')) == 6

    with qtbot.waitSignal(tablewidget.model().sig_data_updated):
        tablewidget.save_edits_action.trigger()

    assert tablewidget.visible_row_count() == 4
    assert len(dbaccessor.get('sonde_installations')) == 4


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
