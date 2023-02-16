# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the Sonde Models library.
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
    mainwindow.librairies_plugin.tabwidget.setCurrentIndex(0)
    tablewidget = mainwindow.librairies_plugin.current_table()

    assert tablewidget.model().name() == 'sonde_brand_models'

    # Wait until data are actually charged in the table.
    qtbot.waitUntil(lambda: tablewidget.visible_row_count() > 0)
    qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)

    yield tablewidget
    # The 'tablewidget' is part of the 'mainwindow' and will get
    # destroyed in the 'mainwindow' fixture.


# =============================================================================
# ---- Tests
# =============================================================================
def test_add_sonde_model(tablewidget, qtbot, dbaccessor, mocker):
    """
    Test that adding a new sonde model is working as expected.
    """
    tablemodel = tablewidget.model()
    assert tablewidget.visible_row_count() == 23
    assert len(dbaccessor.get('sonde_models_lib')) == 23

    # We add a new row and assert that the UI state is as expected.
    tablewidget.new_row_action.trigger()
    assert tablewidget.visible_row_count() == 24
    assert tablemodel.data_edit_count() == 1
    assert tablewidget.get_data_for_row(23) == [''] * 2
    assert tablemodel.is_new_row_at(tablewidget.current_index())
    assert len(dbaccessor.get('sonde_models_lib')) == 23

    # We need to patch the message box that warns the user when
    # a Notnull constraint is violated.
    qmsgbox_patcher = mocker.patch.object(
        QMessageBox, 'exec_', return_value=QMessageBox.Ok)

    # Try to save the changes to the database and assert that a
    # "Notnull constraint violation" message is shown.
    tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 1
    assert tablewidget.visible_row_count() == 24
    assert len(dbaccessor.get('sonde_models_lib')) == 23

    # Enter a non null value for the fields 'sonde_model_id',
    # 'in_repair', 'out_of_order', 'lost', and 'off_network'.
    edited_values = {
        'sonde_brand': 'new_sonde_brand',
        'sonde_model': 'new_sonde_model'}
    for colname, edited_value in edited_values.items():
        col = tablemodel.column_names().index(colname)
        model_index = tablemodel.index(23, col)
        tablewidget.model().set_data_edit_at(model_index, edited_value)
    assert tablewidget.get_data_for_row(23) == [
        'new_sonde_brand', 'new_sonde_model']
    assert tablemodel.data_edit_count() == 3

    # Save the changes to the database.
    with qtbot.waitSignal(tablemodel.sig_data_updated):
        tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 1
    assert tablemodel.data_edit_count() == 0

    sonde_models = dbaccessor.get('sonde_models_lib')
    assert tablewidget.visible_row_count() == 24
    assert len(sonde_models) == 24
    assert sonde_models.iloc[23]['sonde_brand'] == 'new_sonde_brand'
    assert sonde_models.iloc[23]['sonde_model'] == 'new_sonde_model'


def test_edit_sonde_model(tablewidget, qtbot, dbaccessor, obswells_data):
    """
    Test that editing sonde model is working as expected.
    """
    tableview = tablewidget.tableview

    edited_values = {
        'sonde_brand': 'edited_brand',
        'sonde_model': 'edited_model'
        }

    # Edit each editable field of the first row of the table.
    assert tableview.get_data_for_row(0) == ['Solinst', 'LT M10 Gold']
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
    assert tableview.get_data_for_row(0) == ['edited_brand', 'edited_model']

    # Save the changes to the database.
    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get('sonde_models_lib').iloc[0].to_dict()
    for key in edited_values.keys():
        assert saved_values[key] == edited_values[key]


def test_clear_sonde_model(tablewidget, qtbot, dbaccessor):
    """
    Test that clearing sonde model data is working as expected.
    """
    # Note that all attributes of this table are required.
    tableview = tablewidget.tableview
    for col in range(tableview.visible_column_count()):
        current_index = tableview.set_current_index(0, col)
        assert tableview.is_data_required_at(current_index)
        assert not tableview.is_data_clearable_at(current_index)


def test_delete_sonde_model(tablewidget, qtbot, dbaccessor, mocker,
                            dbconnmanager, sondes_data):
    """
    Test that deleting repere data is working as expected.
    """
    assert tablewidget.visible_row_count() == 23
    assert len(dbaccessor.get('sonde_models_lib')) == 23

    # Select and delete the fourth row of the table.
    tablewidget.set_current_index(3, 0)
    assert tablewidget.get_rows_intersecting_selection() == [3]

    tablewidget.delete_row_action.trigger()
    assert tablewidget.model().data_edit_count() == 1

    # Try to save the changes to the database. A foreign constraint error
    # message should appear, so we need to patch the message box.
    qmsgbox_patcher = mocker.patch.object(
        QMessageBox, 'exec_', return_value=QMessageBox.Ok)

    tablewidget.save_edits_action.trigger()
    qtbot.waitUntil(lambda: qmsgbox_patcher.call_count == 1)

    # Change in the database the model of the sondes that are associated with
    # the sonde model that we are trying to delete from the table.
    with qtbot.waitSignal(dbconnmanager.sig_run_tasks_finished, timeout=5000):
        for sonde_id, sonde_data in sondes_data.iterrows():
            if sonde_data['sonde_model_id'] == 4:
                dbconnmanager.set(
                    'sondes_data', sonde_id, {'sonde_model_id': 1},
                    postpone_exec=True)
        dbconnmanager.run_tasks()

    assert tablewidget.visible_row_count() == 23
    assert len(dbaccessor.get('sonde_models_lib')) == 23

    with qtbot.waitSignal(tablewidget.model().sig_data_updated):
        tablewidget.save_edits_action.trigger()

    assert qmsgbox_patcher.call_count == 1
    assert tablewidget.visible_row_count() == 22
    assert len(dbaccessor.get('sonde_models_lib')) == 22


def test_unique_constraint(tablewidget, dbaccessor, qtbot, mocker):
    """
    Test that unique constraint violations are reported as expected.
    """
    tablemodel = tablewidget.model()

    # We need to patch the message box that appears to warn user when
    # a unique constraint is violated.
    qmsgbox_patcher = mocker.patch.object(
        QMessageBox, 'exec_', return_value=QMessageBox.Ok)

    # Set the 'sonde_model' of the second row to that of the first row.
    # Note that the 'sonde_brand' of the first and second row are the same.
    row = 1
    col = tablemodel.column_names().index('sonde_model')
    model_index = tablemodel.index(row, col)
    tablewidget.model().set_data_edit_at(model_index, 'LT M10 Gold')
    assert tablemodel.is_data_edited_at(tablemodel.index(row, col))
    assert tablemodel.data_edit_count() == 1

    # Try to save the changes to the database and assert that a
    # "Unique constraint violation" message is shown as expected.
    tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 1

    # Change the 'sonde_brand' of the second row to a different value than
    # that of the first row.
    col = tablemodel.column_names().index('sonde_brand')
    model_index = tablemodel.index(row, col)
    tablewidget.model().set_data_edit_at(model_index, 'another_sonde_brand')
    assert tablemodel.is_data_edited_at(model_index)
    assert tablemodel.data_edit_count() == 2

    # Save the changes to the database.
    with qtbot.waitSignal(tablemodel.sig_data_updated):
        tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 1
    assert tablemodel.data_edit_count() == 0


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
