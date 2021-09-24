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
from datetime import date
import os
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pandas as pd
import pytest

# ---- Local imports
from sardes.tables import SondesInventoryTableWidget


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def tablewidget(tablesmanager, qtbot, dbaccessor, sondes_data):
    tablewidget = SondesInventoryTableWidget()
    qtbot.addWidget(tablewidget)
    tablewidget.show()

    tablemodel = tablewidget.model()
    tablesmanager.register_table_model(tablemodel)

    # This connection is usually made by the plugin, but we need to make it
    # here manually for testing purposes.
    tablesmanager.sig_models_data_changed.connect(tablemodel.update_data)

    with qtbot.waitSignal(tablemodel.sig_data_updated):
        tablemodel.update_data()
    assert tablewidget.tableview.visible_row_count() == len(sondes_data)

    return tablewidget


# =============================================================================
# ---- Tests
# =============================================================================
def test_add_sondes_data(tablewidget, qtbot, sondes_data, dbaccessor):
    """
    Test that adding a new sonde is working as expected.
    """
    tableview = tablewidget.tableview

    # We add a new row and assert that the UI state is as expected.
    assert tableview.visible_row_count() == len(sondes_data)
    tableview.new_row_action.trigger()
    assert tableview.visible_row_count() == len(sondes_data) + 1
    assert tableview.model().is_new_row_at(tableview.current_index())

    # Save the changes to the database.
    saved_values = dbaccessor.get_sondes_data()
    assert len(saved_values) == len(sondes_data)

    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get_sondes_data()
    assert len(saved_values) == len(sondes_data) + 1


def test_edit_sondes_data(tablewidget, qtbot, dbaccessor):
    """
    Test that editing sonde data is working as expected.
    """
    tableview = tablewidget.tableview

    edited_values = {
        'sonde_model_id': 1,
        'sonde_serial_no': 'edited_sonde_serial_no',
        'date_reception': date(2010, 3, 3),
        'date_withdrawal': date(2010, 3, 30),
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

    saved_values = dbaccessor.get_sondes_data().iloc[0].to_dict()
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
        if tableview.is_data_required_at(current_index):
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

    saved_values = dbaccessor.get_sondes_data().iloc[0].to_dict()
    for attr in clearable_attrs:
        assert pd.isnull(saved_values[attr])


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
