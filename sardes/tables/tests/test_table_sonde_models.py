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

# ---- Local imports
from sardes.tables import SondeModelsTableWidget


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

    # This connection is usually made by the plugin, but we need to make it
    # here manually for testing purposes.
    tablesmanager.sig_models_data_changed.connect(tablemodel.update_data)

    with qtbot.waitSignal(tablemodel.sig_data_updated):
        tablemodel.update_data()
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


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
