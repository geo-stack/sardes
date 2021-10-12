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
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pandas as pd
import pytest
from qtpy.QtWidgets import QMessageBox

# ---- Local imports
from sardes.tables import SondeInstallationsTableWidget
from sardes.widgets.tableviews import MSEC_MIN_PROGRESS_DISPLAY


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def tablewidget(tablesmanager, qtbot, dbaccessor, sondes_installation):
    tablewidget = SondeInstallationsTableWidget()
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

    assert (tablewidget.tableview.visible_row_count() ==
            len(sondes_installation))

    return tablewidget


# =============================================================================
# ---- Tests
# =============================================================================
def test_add_sonde_installations(tablewidget, qtbot, sondes_installation,
                                 dbaccessor):
    """
    Test that adding new sonde installations is working as expected.
    """
    tableview = tablewidget.tableview

    # We add a new row and assert that the UI state is as expected.
    new_row = len(sondes_installation)
    assert tableview.visible_row_count() == len(sondes_installation)
    tableview.new_row_action.trigger()
    assert tableview.visible_row_count() == len(sondes_installation) + 1
    assert tableview.model().is_new_row_at(tableview.current_index())
    assert tableview.get_data_for_row(new_row) == [''] * 6

    # Save the changes to the database.
    saved_values = dbaccessor.get_sonde_installations()
    assert len(saved_values) == len(sondes_installation)

    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get_sonde_installations()
    assert len(saved_values) == len(sondes_installation) + 1


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
        '03037041', 'Solinst Barologger M1.5 - 1016042',
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
        '03040002', 'Solinst LT M10 Gold - 1016387',
        '2010-08-01 12:00', '2010-08-30 19:16', '6.34',
        'Edited sonde install note.']

    # Save the changes to the database.
    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get_sonde_installations().iloc[0].to_dict()
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
        '03037041', 'Solinst Barologger M1.5 - 1016042',
        '2006-08-24 18:00', '2020-12-31 07:14', '9.02',
        'Note for first sonde installation.']
    for col in range(tableview.visible_column_count()):
        current_index = tableview.set_current_index(0, col)
        column = tableview.visible_columns()[col]
        if tableview.is_data_required_at(current_index):
            assert column not in clearable_attrs, column
        else:
            assert column in clearable_attrs, column

            assert not tableview.model().is_data_edited_at(current_index)
            assert not tableview.model().is_null(current_index)
            tableview.clear_item_action.trigger()
            assert tableview.model().is_data_edited_at(current_index)
            assert tableview.model().is_null(current_index)
    assert tableview.get_data_for_row(0) == [
        '03037041', 'Solinst Barologger M1.5 - 1016042',
        '2006-08-24 18:00', '', '9.02', '']

    # Save the changes to the database.
    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get_sonde_installations().iloc[0].to_dict()
    for attr in clearable_attrs:
        assert pd.isnull(saved_values[attr])


def test_delete_sonde_installations(tablewidget, qtbot, dbaccessor, mocker):
    """
    Test that deleting sonde installations is working as expected.
    """
    assert tablewidget.visible_row_count() == 6
    assert len(dbaccessor.get_sonde_installations()) == 6

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
    assert len(dbaccessor.get_sonde_installations()) == 6

    with qtbot.waitSignal(tablewidget.model().sig_data_updated):
        tablewidget.save_edits_action.trigger()

    assert tablewidget.visible_row_count() == 4
    assert len(dbaccessor.get_sonde_installations()) == 4


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
