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
from sardes.tables import SondeModelsTableWidget, SondesInventoryTableModel
from sardes.widgets.tableviews import MSEC_MIN_PROGRESS_DISPLAY


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def tablewidget(tablesmanager, qtbot, dbaccessor):
    tablewidget = SondeModelsTableWidget()
    qtbot.addWidget(tablewidget)
    tablewidget.show()

    tablemodel = tablewidget.model()
    tablesmanager.register_table_model(tablemodel)

    # We also need to register table models that have foreign relation
    # with the table Sonde Models.
    tablesmanager.register_table_model(SondesInventoryTableModel())

    # This connection is usually made by the plugin, but we need to make it
    # here manually for testing purposes.
    tablesmanager.sig_models_data_changed.connect(tablemodel.update_data)

    with qtbot.waitSignal(tablemodel.sig_data_updated):
        tablemodel.update_data()
    qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)

    assert tablewidget.tableview.visible_row_count() == 23

    return tablewidget


# =============================================================================
# ---- Tests
# =============================================================================
def test_add_sonde_model(tablewidget, qtbot, dbaccessor):
    """
    Test that adding a new sonde model is working as expected.
    """
    tableview = tablewidget.tableview

    # We add a new row and assert that the UI state is as expected.
    assert tableview.visible_row_count() == 23
    tableview.new_row_action.trigger()
    assert tableview.visible_row_count() == 23 + 1
    assert tableview.model().is_new_row_at(tableview.current_index())

    # Save the changes to the database.
    saved_values = dbaccessor.get_sonde_models_lib()
    assert len(saved_values) == 23

    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get_sonde_models_lib()
    assert len(saved_values) == 23 + 1


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

    saved_values = dbaccessor.get_sonde_models_lib().iloc[0].to_dict()
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


def test_delete_sonde_model(tablewidget, qtbot, dbaccessor, mocker,
                            dbconnmanager, sondes_data):
    """
    Test that deleting repere data is working as expected.
    """
    assert tablewidget.visible_row_count() == 23
    assert len(dbaccessor.get_sonde_models_lib()) == 23

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
    assert len(dbaccessor.get_sonde_models_lib()) == 23

    with qtbot.waitSignal(tablewidget.model().sig_data_updated):
        tablewidget.save_edits_action.trigger()

    assert qmsgbox_patcher.call_count == 1
    assert tablewidget.visible_row_count() == 22
    assert len(dbaccessor.get_sonde_models_lib()) == 22


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
