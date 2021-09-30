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
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pandas as pd
import pytest

# ---- Local imports
from sardes.tables import RepereTableWidget
from sardes.widgets.tableviews import MSEC_MIN_PROGRESS_DISPLAY


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def tablewidget(tablesmanager, qtbot, dbaccessor, repere_data):
    tablewidget = RepereTableWidget()
    qtbot.addWidget(tablewidget)
    tablewidget.show()

    tablemodel = tablewidget.model()
    tablesmanager.register_table_model(tablemodel)

    # This connection is usually made by the plugin, but we need to make it
    # here manually for testing purposes.
    tablesmanager.sig_models_data_changed.connect(tablemodel.update_data)

    with qtbot.waitSignal(tablemodel.sig_data_updated):
        tablemodel.update_data()
    qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)

    assert tablewidget.tableview.visible_row_count() == len(repere_data)

    return tablewidget


# =============================================================================
# ---- Tests
# =============================================================================
def test_add_repere_data(tablewidget, qtbot, repere_data, dbaccessor):
    """
    Test that adding a new repere is working as expected.
    """
    tableview = tablewidget.tableview

    # We add a new row and assert that the UI state is as expected.
    assert tableview.visible_row_count() == len(repere_data)
    tableview.new_row_action.trigger()
    assert tableview.visible_row_count() == len(repere_data) + 1
    assert tableview.model().is_new_row_at(tableview.current_index())

    # Save the changes to the database.
    saved_values = dbaccessor.get_repere_data()
    assert len(saved_values) == len(repere_data)

    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get_repere_data()
    assert len(saved_values) == len(repere_data) + 1


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
        '03037041', '9.3', '1.3', '2009-07-14 09:00', '2020-08-03 19:14',
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
        '02200001', '10.1', '0.7', '2009-07-14 00:00', '2020-08-03 07:14',
        'No', 'Edited repere note.']

    # Save the changes to the database.
    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get_repere_data().iloc[0].to_dict()
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
        '03037041', '9.3', '1.3', '2009-07-14 09:00', '2020-08-03 19:14',
        'Yes', 'Repere note #1']
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
        '03037041', '9.3', '1.3', '2009-07-14 09:00', '', 'Yes', '']

    # Save the changes to the database.
    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get_repere_data().iloc[0].to_dict()
    for attr in clearable_attrs:
        assert pd.isnull(saved_values[attr])


def test_repere_data(tablewidget, qtbot, dbaccessor, mocker, dbconnmanager):
    """
    Test that deleting repere data is working as expected.
    """
    assert tablewidget.visible_row_count() == 5
    assert len(dbaccessor.get_repere_data()) == 5

    # Select and delete the first two rows of the table.
    tablewidget.set_current_index(0, 0)
    tablewidget.select(1, 0)
    assert tablewidget.get_rows_intersecting_selection() == [0, 1]

    tablewidget.delete_row_action.trigger()
    assert tablewidget.model().data_edit_count() == 1

    # Save the changes to the database.
    repere_data = dbaccessor.get_repere_data()
    assert len(repere_data) == 5

    with qtbot.waitSignal(tablewidget.model().sig_data_updated):
        tablewidget.save_edits_action.trigger()

    repere_data = dbaccessor.get_repere_data()
    assert len(repere_data) == 3


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
