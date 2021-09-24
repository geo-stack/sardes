# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the Observation Wells table.
"""

# ---- Standard imports
import os
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import numpy as np
import pandas as pd
import pytest
from qtpy.QtCore import Qt, QUrl
from qtpy.QtGui import QDesktopServices

# ---- Local imports
from sardes.api.timeseries import DataType
from sardes.tables import ObsWellsTableWidget
from sardes.widgets.tableviews import MSEC_MIN_PROGRESS_DISPLAY


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def tablewidget(tablesmanager, qtbot, dbaccessor, obswells_data):
    tablewidget = ObsWellsTableWidget()
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

    assert tablewidget.tableview.visible_row_count() == len(obswells_data)

    return tablewidget


# =============================================================================
# ---- Tests
# =============================================================================
def test_show_in_google_maps(tablewidget, qtbot, mocker):
    """
    Test that the tool to show the currently selected well in Google maps is
    working as expected.
    """
    tableview = tablewidget.tableview

    # We are selecting the first well in the table.
    tableview.set_current_index(0, 0)

    # We are patching QDesktopServices.openUrl because we don't want to
    # slow down tests by opening web pages on an external browser.
    patcher_qdesktopservices = mocker.patch.object(
        QDesktopServices, 'openUrl', return_value=True)
    tablewidget.show_in_google_maps()
    patcher_qdesktopservices.assert_called_once_with(QUrl(
        'https://www.google.com/maps/search/?api=1&query=45.445178,-72.828773'
        ))


def test_select_observation_well(tablewidget, qtbot):
    """
    Test that selecting an observation well is working as expected.
    """
    tableview = tablewidget.tableview

    # We select the first well in the table and we assert that
    # the UI state is as expected.
    tableview.set_current_index(0, 0)

    assert not tablewidget.model().is_new_row_at(tableview.current_index())
    assert tablewidget.show_data_btn.isEnabled()
    assert tablewidget.show_gmap_btn.isEnabled()
    assert tablewidget.construction_logs_manager.isEnabled()
    assert tablewidget.water_quality_reports.isEnabled()


def test_add_observation_well(tablewidget, qtbot, obswells_data, dbaccessor):
    """
    Test that adding a new observation well is working as expected.
    """
    tableview = tablewidget.tableview

    # We add a new row and assert that the UI state is as expected.
    assert tableview.visible_row_count() == len(obswells_data)
    tableview.new_row_action.trigger()
    assert tableview.visible_row_count() == len(obswells_data) + 1

    assert tableview.model().is_new_row_at(tableview.current_index())
    assert not tablewidget.show_data_btn.isEnabled()
    assert not tablewidget.construction_logs_manager.isEnabled()
    assert not tablewidget.water_quality_reports.isEnabled()

    # Save the changes to the database.
    db_obswell_data = dbaccessor.get_observation_wells_data()
    assert len(db_obswell_data) == len(obswells_data)

    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    db_obswell_data = dbaccessor.get_observation_wells_data()
    assert len(db_obswell_data) == len(obswells_data) + 1


def test_edit_observation_well(tablewidget, qtbot, obswells_data, dbaccessor):
    """
    Test that editing observation well data is working as expected.
    """
    tableview = tablewidget.tableview

    edited_values = {
        'obs_well_id': 'edited_obs_well_id',
        'municipality': 'edited_municipality',
        'common_name': 'edited_common_name',
        'latitude': 42.424242,
        'longitude': -65.656565,
        'aquifer_type': 'edited_aquifer_type',
        'confinement': 'edited_confinement',
        'aquifer_code': 999,
        'in_recharge_zone': 'edited_in_recharge_zone',
        'is_influenced': 'edited_is_influenced',
        'is_station_active': False,
        'obs_well_notes': 'edited_obs_well_notes'
        }

    wlvl = dbaccessor.get_timeseries_for_obs_well(
        obswells_data.index[0], [DataType.WaterLevel])[DataType.WaterLevel]

    # Edit each editable field of the first row of the table.
    assert tableview.get_data_for_row(0) == [
        '03037041', "St-Paul-d'Abbotsford", "Saint-Paul-d'Abbotsford",
        'MT', '3', 'Confined', 'No', 'No', '45.445178', '-72.828773',
        '2015-01-01', '2020-12-31', str(np.round(np.mean(wlvl), 3)),
        'Yes', 'Note for well 03037041']
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
        'edited_obs_well_id', 'edited_common_name', 'edited_municipality',
        'edited_aquifer_type', '999', 'edited_confinement',
        'edited_in_recharge_zone', 'edited_is_influenced',
        '42.424242', '-65.656565', '2015-01-01', '2020-12-31',
        str(np.round(np.mean(wlvl), 3)), 'No', 'edited_obs_well_notes']

    # Save the changes to the database.
    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get_observation_wells_data().iloc[0].to_dict()
    for key in edited_values.keys():
        assert saved_values[key] == edited_values[key]


def test_clear_observation_well(tablewidget, qtbot, dbaccessor, obswells_data):
    """
    Test that clearing observation well data is working as expected.
    """
    tableview = tablewidget.tableview
    clearable_attrs = [
        'municipality', 'common_name', 'latitude', 'longitude',
        'aquifer_type', 'confinement', 'aquifer_code', 'in_recharge_zone',
        'is_influenced', 'obs_well_notes'
        ]

    wlvl = dbaccessor.get_timeseries_for_obs_well(
        obswells_data.index[0], [DataType.WaterLevel])[DataType.WaterLevel]

    # Clear each non required field of the first row of the table.
    assert tableview.get_data_for_row(0) == [
        '03037041', "St-Paul-d'Abbotsford", "Saint-Paul-d'Abbotsford",
        'MT', '3', 'Confined', 'No', 'No', '45.445178', '-72.828773',
        '2015-01-01', '2020-12-31', str(np.round(np.mean(wlvl), 3)),
        'Yes', 'Note for well 03037041']
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
        '03037041', '', '', '', '', '', '', '', '', '',
        '2015-01-01', '2020-12-31', str(np.round(np.mean(wlvl), 3)), 'Yes', '']

    # Save the changes to the database.
    with qtbot.waitSignal(tableview.model().sig_data_updated):
        tableview._save_data_edits(force=True)

    saved_values = dbaccessor.get_observation_wells_data().iloc[0].to_dict()
    for attr in clearable_attrs:
        assert pd.isnull(saved_values[attr])


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
