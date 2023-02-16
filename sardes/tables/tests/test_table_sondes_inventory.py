# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the Sondes Inventory table.
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
from sardes.widgets.tableviews import MSEC_MIN_PROGRESS_DISPLAY


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def tablewidget(mainwindow, qtbot, dbaccessor):
    mainwindow.tables_plugin.switch_to_plugin()
    mainwindow.tables_plugin.tabwidget.setCurrentIndex(1)
    tablewidget = mainwindow.tables_plugin.current_table()

    assert tablewidget.model().name() == 'table_sondes_inventory'

    # Wait until data are actually charged in the table.
    qtbot.waitUntil(lambda: tablewidget.visible_row_count() > 0)
    qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)

    yield tablewidget
    # The 'tablewidget' is part of the 'mainwindow' and will get
    # destroyed in the 'mainwindow' fixture.


# =============================================================================
# ---- Tests
# =============================================================================
def test_add_sondes_data(tablewidget, dbaccessor, qtbot, mocker):
    """
    Test that adding a new sonde is working as expected.
    """
    tablemodel = tablewidget.model()
    assert tablewidget.visible_row_count() == 6
    assert len(dbaccessor.get('sondes_data')) == 6

    # We add a new row and assert that the UI state is as expected.
    tablewidget.new_row_action.trigger()
    assert tablewidget.visible_row_count() == 7
    assert tablemodel.data_edit_count() == 1
    assert tablewidget.get_data_for_row(6) == [
        '', '', '', '', 'No', 'No', 'No', 'No', '']
    assert tablemodel.is_new_row_at(tablewidget.current_index())
    assert len(dbaccessor.get('sondes_data')) == 6

    # We need to patch the message box that warns the user when
    # a Notnull constraint is violated.
    qmsgbox_patcher = mocker.patch.object(
        QMessageBox, 'exec_', return_value=QMessageBox.Ok)

    # Try to save the changes to the database and assert that a
    # "Notnull constraint violation" message is shown.
    tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 1
    assert tablewidget.visible_row_count() == 7
    assert len(dbaccessor.get('sondes_data')) == 6

    # Enter a non null value for the fields 'sonde_model_id',
    # 'in_repair', 'out_of_order', 'lost', and 'off_network'.
    edited_values = {
        'sonde_model_id': 2,
        'in_repair': True,
        'out_of_order': True,
        'lost': True,
        'off_network': True}
    for colname, edited_value in edited_values.items():
        col = tablemodel.column_names().index(colname)
        model_index = tablemodel.index(6, col)
        tablewidget.model().set_data_edit_at(model_index, edited_value)
    assert tablewidget.get_data_for_row(6) == [
        'Solinst Barologger M1.5 Gold', '', '', '',
        'Yes', 'Yes', 'Yes', 'Yes', '']
    assert tablemodel.data_edit_count() == 6

    # Save the changes to the database.
    with qtbot.waitSignal(tablemodel.sig_data_updated):
        tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 1
    assert tablemodel.data_edit_count() == 0

    sondes_data = dbaccessor.get('sondes_data')
    assert tablewidget.visible_row_count() == 7
    assert len(sondes_data) == 7
    assert sondes_data.iloc[6]['sonde_model_id'] == 2
    assert sondes_data.iloc[6]['in_repair'] == True
    assert sondes_data.iloc[6]['out_of_order'] == True
    assert sondes_data.iloc[6]['lost'] == True
    assert sondes_data.iloc[6]['off_network'] == True


def test_edit_sondes_data(tablewidget, qtbot, dbaccessor):
    """
    Test that editing sonde data is working as expected.
    """
    tableview = tablewidget.tableview

    edited_values = {
        'sonde_model_id': 1,
        'sonde_serial_no': 'edited_sonde_serial_no',
        'date_reception': datetime(2010, 3, 3),
        'date_withdrawal': datetime(2010, 3, 30),
        'in_repair': True,
        'out_of_order': True,
        'lost': True,
        'off_network': True,
        'sonde_notes': 'Edited sonde note.'
        }

    # Edit each editable field of the first row of the table.
    assert tableview.get_data_for_row(0) == [
        'Solinst Barologger M1.5', '1016042', '2006-03-30', '2020-12-31',
        'No', 'No', 'No', 'No', 'Note sonde 1016042.']
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
        'Solinst LT M10 Gold', 'edited_sonde_serial_no',
        '2010-03-03', '2010-03-30',
        'Yes', 'Yes', 'Yes', 'Yes', 'Edited sonde note.']

    # Save the changes to the database.
    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get('sondes_data').iloc[0].to_dict()
    for key in edited_values.keys():
        assert saved_values[key] == edited_values[key]


def test_clear_sondes_data(tablewidget, qtbot, dbaccessor):
    """
    Test that clearing sonde data is working as expected.
    """
    tableview = tablewidget.tableview
    clearable_attrs = [
        'sonde_serial_no', 'date_reception', 'date_withdrawal', 'sonde_notes']

    # Clear each non required field of the first row of the table.
    assert tableview.get_data_for_row(0) == [
        'Solinst Barologger M1.5', '1016042', '2006-03-30', '2020-12-31',
        'No', 'No', 'No', 'No', 'Note sonde 1016042.']
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
        'Solinst Barologger M1.5', '', '', '', 'No', 'No', 'No', 'No', '']

    # Save the changes to the database.
    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get('sondes_data').iloc[0].to_dict()
    for attr in clearable_attrs:
        assert pd.isnull(saved_values[attr])


def test_delete_sondes_data(tablewidget, qtbot, dbaccessor, mocker,
                            dbconnmanager):
    """
    Test that deleting a sonde from the database is working as expected.
    """
    assert tablewidget.visible_row_count() == 6
    assert len(dbaccessor.get('sondes_data')) == 6

    # Select and delete the second row of the table.
    tablewidget.set_current_index(1, 0)
    assert tablewidget.get_rows_intersecting_selection() == [1]

    tablewidget.delete_row_action.trigger()
    assert tablewidget.model().data_edit_count() == 1

    # Try to save the changes to the database. A foreign constraint error
    # message should appear, so we need to patch the message box.
    qmsgbox_patcher = mocker.patch.object(
        QMessageBox, 'exec_', return_value=QMessageBox.Ok)

    tablewidget.save_edits_action.trigger()
    qtbot.waitUntil(lambda: qmsgbox_patcher.call_count == 1)

    # Delete from the database the sonde installations that are causing
    # a foreign constraint violations when we try to delete the sonde on the
    # second row of the table.
    with qtbot.waitSignal(dbconnmanager.sig_run_tasks_finished, timeout=5000):
        sonde_uuid = dbaccessor.get('sondes_data').index[1]
        sonde_installs = dbaccessor.get('sonde_installations')
        sonde_install_ids = sonde_installs.index[
            sonde_installs['sonde_uuid'] == sonde_uuid]
        dbconnmanager.delete('sonde_installations', sonde_install_ids)

    assert tablewidget.visible_row_count() == 6
    assert len(dbaccessor.get('sondes_data')) == 6

    with qtbot.waitSignal(tablewidget.model().sig_data_updated):
        tablewidget.save_edits_action.trigger()

    assert qmsgbox_patcher.call_count == 1
    assert tablewidget.visible_row_count() == 5
    assert len(dbaccessor.get('sondes_data')) == 5


def test_unique_constraint(tablewidget, dbaccessor, qtbot, mocker):
    """
    Test that unique constraint violations are reported as expected.
    """
    tablemodel = tablewidget.model()

    # We need to patch the message box that appears to warn user when
    # a unique constraint is violated.
    qmsgbox_patcher = mocker.patch.object(
        QMessageBox, 'exec_', return_value=QMessageBox.Ok)

    # Set the 'sonde_serial_no' of the second row to none.
    # Note that the 'sonde_model_id' of the first and second row are the same.
    row = 1
    col = tablemodel.column_names().index('sonde_serial_no')
    model_index = tablemodel.index(row, col)
    tablewidget.model().clear_model_data_at(model_index)
    assert tablemodel.is_data_edited_at(tablemodel.index(row, col))
    assert tablewidget.model().is_null(model_index)
    assert tablemodel.data_edit_count() == 1

    # Save the changes to the database.
    with qtbot.waitSignal(tablemodel.sig_data_updated):
        tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 0
    assert not tablemodel.is_data_edited_at(tablemodel.index(row, col))
    assert tablemodel.data_edit_count() == 0

    # Set the 'sonde_serial_no' of the second row as that of the first row.
    tablewidget.model().set_data_edit_at(model_index, '1016042')
    assert tablemodel.is_data_edited_at(model_index)
    assert tablemodel.data_edit_count() == 1

    # Try to save the changes to the database and assert that a
    # "Unique constraint violation" message is shown as expected.
    tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 1

    # Change the 'sonde_model_id' of the second to a different sonde than
    # that of the first row.
    col = tablemodel.column_names().index('sonde_model_id')
    model_index = tablemodel.index(row, col)
    tablewidget.model().set_data_edit_at(model_index, 1)
    assert tablemodel.is_data_edited_at(model_index)
    assert tablemodel.data_edit_count() == 2

    # Save the changes to the database.
    with qtbot.waitSignal(tablemodel.sig_data_updated):
        tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 1
    assert tablemodel.data_edit_count() == 0


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
