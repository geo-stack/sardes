# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the HG Values table.
"""

# ---- Standard imports
from datetime import datetime
import os
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pytest

# ---- Local imports
from sardes.utils.data_operations import are_values_equal
from sardes.widgets.tableviews import MSEC_MIN_PROGRESS_DISPLAY


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def tablewidget(mainwindow, qtbot, dbaccessor):
    mainwindow.hydrogeochemistry_plugin.switch_to_plugin()
    mainwindow.hydrogeochemistry_plugin.tabwidget.setCurrentIndex(2)
    tablewidget = mainwindow.hydrogeochemistry_plugin.current_table()

    assert tablewidget.model().name() == 'table_hg_param_values'

    # Wait until data are actually charged in the table.
    qtbot.waitUntil(lambda: tablewidget.visible_row_count() > 0)
    qtbot.wait(MSEC_MIN_PROGRESS_DISPLAY + 100)

    yield tablewidget
    # The 'tablewidget' is part of the 'mainwindow' and will get
    # destroyed in the 'mainwindow' fixture.


# =============================================================================
# ---- Tests
# =============================================================================
def test_import_hglab_report_tool(tablewidget, qtbot, dbaccessor, mocker):
    """
    Test that adding new manual measurements is working as expected.
    """
    import_hglab_tool = tablewidget.import_hglab_tool

    assert import_hglab_tool.toolwidget() is None
    import_hglab_tool.trigger()
    assert import_hglab_tool.toolwidget().isVisible()


def test_add_and_edit(tablewidget, qtbot, dbaccessor, mocker):
    """
    Test that adding and editing a new row is working as expected.
    """
    tableview = tablewidget.tableview
    tablemodel = tablewidget.model()

    assert tableview.visible_row_count() == 4
    assert list(dbaccessor.get('hg_param_values').index) == [1, 2, 3, 4]

    # We add a new row to the table.
    tableview.new_row_action.trigger()
    assert tableview.visible_row_count() == 4 + 1
    assert tableview.get_data_for_row(4) == [''] * 10

    # Enter a non null value for the fields that are required.
    edited_values = {
        'hg_survey_id': 4,
        'hg_param_id': 3,
        'hg_param_value': '24.7',
        'lim_detection': 12.33,
        'meas_units_id': 2,
        'lab_sample_id': 'sample#test',
        'lab_report_date': datetime(2015, 4, 23, 12, 30),
        'lab_id': 1,
        'method': 'Method#4',
        'notes': 'Test add and edit new row.'
        }
    for colname, edited_value in edited_values.items():
        col = tablemodel.column_names().index(colname)
        model_index = tablemodel.index(4, col)
        tablewidget.model().set_data_edit_at(model_index, edited_value)

    assert tablewidget.get_data_for_row(4) == [
        '02167001 - 2019-09-09 00:00', 'PARAM#3', '24.7', '12.33',
        'µmhos/cm', 'sample#test', '2015-04-23', 'lab#1', 'Method#4',
        'Test add and edit new row.'
        ]

    # Save the changes in the database.
    with qtbot.waitSignal(tablemodel.sig_data_updated):
        tablewidget.save_edits_action.trigger()

    saved_values = dbaccessor.get('hg_param_values')
    assert list(saved_values.index) == [1, 2, 3, 4, 5]
    for name, val1 in edited_values.items():
        val2 = saved_values.iloc[-1][name]
        assert are_values_equal(val1, val2)


def test_clear_cells(tablewidget, qtbot, dbaccessor):
    """Test that clearing table cells is working as expected."""
    tableview = tablewidget.tableview

    # Clear each non required field of the first row of the table.
    assert tableview.get_data_for_row(0) == [
        '03037041 - 2011-08-02 15:20', 'PARAM#3', '> 0.345', '0.345',
        'µg/L', 'Sample#1', '2017-11-15', 'lab#1', 'Method #1', 'Note #1']

    for col in range(tableview.visible_column_count()):
        current_index = tableview.set_current_index(0, col)
        if tableview.is_data_clearable_at(current_index):
            tableview.clear_item_action.trigger()

    assert tableview.get_data_for_row(0) == [
        '03037041 - 2011-08-02 15:20', 'PARAM#3', '> 0.345',
        ] + [''] * 7

    # Save the changes to the database.
    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = list(dbaccessor.get('hg_param_values').iloc[0].values)
    expected_values = [1, 3, '> 0.345'] + [None] * 7
    for val1, val2 in zip(saved_values, expected_values):
        assert are_values_equal(val1, val2)


def test_delete_row(tablewidget, qtbot, dbaccessor):
    """Test that deleting a row in the table is working as expected."""
    assert tablewidget.visible_row_count() == 4
    assert list(dbaccessor.get('hg_param_values').index) == [1, 2, 3, 4]

    # Select and delete the first two rows of the table.
    tablewidget.set_current_index(0, 0)
    tablewidget.select(1, 0)
    tablewidget.delete_row_action.trigger()

    # Save the changes to the database.
    with qtbot.waitSignal(tablewidget.model().sig_data_updated):
        tablewidget.save_edits_action.trigger()

    assert tablewidget.visible_row_count() == 4 - 2
    assert list(dbaccessor.get('hg_param_values').index) == [3, 4]


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])