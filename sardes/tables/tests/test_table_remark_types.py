# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the Remark Types table.
"""

# ---- Standard imports
import os
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pytest
from qtpy.QtWidgets import QMessageBox

# ---- Local imports
from sardes.widgets.tableviews import MSEC_MIN_PROGRESS_DISPLAY


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def tablewidget(mainwindow, qtbot, dbaccessor):
    mainwindow.librairies_plugin.switch_to_plugin()
    mainwindow.librairies_plugin.tabwidget.setCurrentIndex(1)
    tablewidget = mainwindow.librairies_plugin.current_table()

    assert tablewidget.model().name() == 'table_remark_types'

    # Wait until data are actually charged in the table.
    qtbot.waitUntil(lambda: tablewidget.visible_row_count() > 0)
    qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)

    yield tablewidget
    # The 'tablewidget' is part of the 'mainwindow' and will get
    # destroyed in the 'mainwindow' fixture.


# =============================================================================
# ---- Tests
# =============================================================================
def test_add_and_edit_remark_type(tablewidget, qtbot, dbaccessor, mocker):
    """
    Test that adding a new remark type is working as expected.
    """
    tablemodel = tablewidget.model()
    assert tablewidget.visible_row_count() == 2
    assert len(dbaccessor.get('remark_types')) == 2

    # Add a new row and assert that the UI state is as expected.
    tablewidget.new_row_action.trigger()
    assert tablewidget.visible_row_count() == 3
    assert tablemodel.data_edit_count() == 1
    assert tablewidget.get_data_for_row(2) == [''] * 3
    assert tablemodel.is_new_row_at(tablewidget.current_index())
    assert len(dbaccessor.get('remark_types')) == 2

    # Patch the message box that warns the user when
    # a Notnull constraint is violated.
    qmsgbox_patcher = mocker.patch.object(
        QMessageBox, 'exec_', return_value=QMessageBox.Ok)

    # Try to save the changes to the database and assert that a
    # "Notnull constraint violation" message is shown.
    tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 1
    assert tablewidget.visible_row_count() == 3
    assert len(dbaccessor.get('remark_types')) == 2

    # Enter non null values for the new remark type.
    new_remark_type_data = {
        'remark_type_code': 'R3',
        'remark_type_name': 'remark type 3',
        'remark_type_desc': 'desc remark type 3'}
    for colname, edited_value in new_remark_type_data.items():
        col = tablemodel.column_names().index(colname)
        model_index = tablemodel.index(2, col)
        tablewidget.model().set_data_edit_at(model_index, edited_value)
    assert tablewidget.get_data_for_row(2) == list(
        new_remark_type_data.values())
    assert tablemodel.data_edit_count() == 4

    # Save the changes to the database.
    with qtbot.waitSignal(tablemodel.sig_data_updated):
        tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 1
    assert tablemodel.data_edit_count() == 0

    remark_types = dbaccessor.get('remark_types')
    assert tablewidget.visible_row_count() == 3
    assert len(remark_types) == 3
    for field, value in new_remark_type_data.items():
        assert remark_types.iloc[2][field] == value


def test_clear_remark_type(tablewidget, qtbot, dbaccessor):
    """
    Test that clearing remark type data is working as expected.
    """
    tableview = tablewidget.tableview

    # Clear each non required field of the first row of the table.
    # Note that there is only one column that is clearable in this table.
    assert tableview.get_data_for_row(0) == [
        'C', 'Correction', 'Correction made on the monitoring data.']
    for col in range(tableview.visible_column_count()):
        tableview.set_current_index(0, col)
        tableview.clear_item_action.trigger()
    assert tableview.get_data_for_row(0) == ['C', 'Correction', '']
    assert tableview.model().data_edit_count() == 1

    # Save the changes to the database.
    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    remark_types = dbaccessor.get('remark_types')
    assert list(remark_types.iloc[0].values) == ['C', 'Correction', None]


def test_delete_remark_types(tablewidget, qtbot, dbaccessor, mocker,
                             dbconnmanager):
    """
    Test that deleting remark type is working as expected.
    """
    assert tablewidget.visible_row_count() == 2
    assert len(dbaccessor.get('remark_types')) == 2

    # Select and delete the first row of the table.
    tablewidget.set_current_index(0, 0)
    tablewidget.delete_row_action.trigger()
    assert tablewidget.model().data_edit_count() == 1

    # Try to save the changes to the database. A foreign constraint error
    # message should appear, so we need to patch the message box.
    qmsgbox_patcher = mocker.patch.object(
        QMessageBox, 'exec_', return_value=QMessageBox.Ok)

    tablewidget.save_edits_action.trigger()
    qtbot.waitUntil(lambda: qmsgbox_patcher.call_count == 1)

    # Remove the foreign constraints.
    remarks = dbaccessor.get('remarks')
    with qtbot.waitSignal(dbconnmanager.sig_run_tasks_finished, timeout=5000):
        for remark_id, remark_data in remarks.iterrows():
            if remark_data['remark_type_id'] == 1:
                dbconnmanager.set(
                    'remarks', remark_id, {'remark_type_id': 2},
                    postpone_exec=True)
        dbconnmanager.run_tasks()

    # Try to save the changes again.
    with qtbot.waitSignal(tablewidget.model().sig_data_updated):
        tablewidget.save_edits_action.trigger()

    assert qmsgbox_patcher.call_count == 1
    assert tablewidget.visible_row_count() == 1
    assert len(dbaccessor.get('remark_types')) == 1


def test_unique_constraint(tablewidget, dbaccessor, qtbot, mocker):
    """
    Test that unique constraint violations are reported as expected.
    """
    model = tablewidget.model()

    # We need to patch the message box that appears to warn user when
    # a unique constraint is violated.
    qmsgbox_patcher = mocker.patch.object(
        QMessageBox, 'exec_', return_value=QMessageBox.Ok)

    # Set the 'remark_type_code' of the second row to that of the first row.
    row = 1
    col = model.column_names().index('remark_type_code')
    model_index = model.index(row, col)
    model.set_data_edit_at(model_index, 'C')
    assert model.is_data_edited_at(model.index(row, col))
    assert model.data_edit_count() == 1

    # Try to save the changes to the database and assert that a
    # "Unique constraint violation" message is shown as expected.
    tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 1

    # Clear edits.
    tablewidget.cancel_edits_action.trigger()
    assert model.data_edit_count() == 0

    # Set the 'remark_type_name' of the second row to that of the first row.
    row = 1
    col = model.column_names().index('remark_type_name')
    model_index = model.index(row, col)
    model.set_data_edit_at(model_index, 'Correction')
    assert model.is_data_edited_at(model.index(row, col))
    assert model.data_edit_count() == 1

    # Try to save the changes to the database and assert that a
    # "Unique constraint violation" message is shown as expected.
    tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 2


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
