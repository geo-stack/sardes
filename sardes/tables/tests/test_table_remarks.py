# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the Remarks table.
"""

# ---- Standard imports
import os
from datetime import datetime
from uuid import UUID
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pytest
import pandas as pd
from qtpy.QtWidgets import QMessageBox

# ---- Local imports
from sardes.widgets.tableviews import MSEC_MIN_PROGRESS_DISPLAY


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def tablewidget(mainwindow, qtbot, dbaccessor):
    mainwindow.tables_plugin.switch_to_plugin()
    mainwindow.tables_plugin.tabwidget.setCurrentIndex(5)
    tablewidget = mainwindow.tables_plugin.current_table()

    assert tablewidget.model().name() == 'table_remarks'

    # Wait until data are actually charged in the table.
    qtbot.waitUntil(lambda: tablewidget.visible_row_count() > 0)
    qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)

    yield tablewidget
    # The 'tablewidget' is part of the 'mainwindow' and will get
    # destroyed in the 'mainwindow' fixture.


# =============================================================================
# ---- Tests
# =============================================================================
def test_add_and_edit_remark(tablewidget, qtbot, dbaccessor, mocker):
    """
    Test that adding a new remark is working as expected.
    """
    tablemodel = tablewidget.model()
    assert tablewidget.visible_row_count() == 2
    assert len(dbaccessor.get('remarks')) == 2

    # Add a new row and assert that the UI state is as expected.
    tablewidget.new_row_action.trigger()
    assert tablewidget.visible_row_count() == 3
    assert tablemodel.data_edit_count() == 1
    assert tablewidget.get_data_for_row(2) == [''] * 7
    assert tablemodel.is_new_row_at(tablewidget.current_index())
    assert len(dbaccessor.get('remarks')) == 2

    # Patch the message box that warns the user when
    # a Notnull constraint is violated.
    qmsgbox_patcher = mocker.patch.object(
        QMessageBox, 'exec_', return_value=QMessageBox.Ok)

    # Try to save the changes to the database and assert that a
    # "Notnull constraint violation" message is shown.
    tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 1
    assert tablewidget.visible_row_count() == 3
    assert len(dbaccessor.get('remarks')) == 2

    # Enter non null values for the new remark type.
    new_remark_data = {
        'sampling_feature_uuid': UUID('dcc36634-ae7e-42c0-966d-77f575232ead'),
        'remark_type_id': 1,
        'period_start': datetime(2006, 6, 6, 6),
        'period_end': datetime(2009, 9, 9, 9),
        'remark_text': 'remark text no.3',
        'remark_author': 'remark author no.3',
        'remark_date': datetime(2022, 2, 2, 2),
        }
    for colname, edited_value in new_remark_data.items():
        col = tablemodel.column_names().index(colname)
        model_index = tablemodel.index(2, col)
        tablewidget.model().set_data_edit_at(model_index, edited_value)
    assert tablewidget.get_data_for_row(2) == [
        '02200001',
        'Correction',
        '2006-06-06 06:00',
        '2009-09-09 09:00',
        'remark text no.3',
        'remark author no.3',
        '2022-02-02',
        ]
    assert tablemodel.data_edit_count() == 8

    # Save the changes to the database.
    with qtbot.waitSignal(tablemodel.sig_data_updated):
        tablewidget.save_edits_action.trigger()
    assert qmsgbox_patcher.call_count == 1
    assert tablemodel.data_edit_count() == 0

    remarks = dbaccessor.get('remarks')
    assert tablewidget.visible_row_count() == 3
    assert len(remarks) == 3
    for field, value in new_remark_data.items():
        assert remarks.iloc[2][field] == value


def test_clear_remark(tablewidget, qtbot, dbaccessor):
    """
    Test that clearing a remark is working as expected.
    """
    tableview = tablewidget.tableview

    # Clear each non required field of the first row of the table.
    # Note that there is only one column that is clearable in this table.
    assert tableview.get_data_for_row(0) == [
        '03037041', 'Correction', '2011-08-24 18:00', '2012-02-05 06:15',
        'text_remark_1', 'author_remark_1', '2022-06-23']
    for col in range(tableview.visible_column_count()):
        tableview.set_current_index(0, col)
        tableview.clear_item_action.trigger()
    assert tableview.get_data_for_row(0) == [
        '03037041', '', '', '', '', '', '']
    assert tableview.model().data_edit_count() == 6

    # Save the changes to the database.
    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    remarks = dbaccessor.get('remarks')
    assert list(remarks.iloc[0].values) == [
        UUID('3c6d0e15-6775-4304-964a-5db89e463c55'),
        pd.NA, pd.NaT, pd.NaT, None, None, pd.NaT]


def test_delete_remarks(tablewidget, qtbot, dbaccessor, mocker):
    """
    Test that deleting a remark is working as expected.
    """
    assert tablewidget.visible_row_count() == 2
    assert len(dbaccessor.get('remarks')) == 2

    # Select and delete the first row of the table.
    tablewidget.set_current_index(0, 0)
    tablewidget.delete_row_action.trigger()
    assert tablewidget.model().data_edit_count() == 1

    # Save the changes.
    with qtbot.waitSignal(tablewidget.model().sig_data_updated):
        tablewidget.save_edits_action.trigger()

    assert tablewidget.visible_row_count() == 1
    assert len(dbaccessor.get('remarks')) == 1


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
