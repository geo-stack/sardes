# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Third party imports
import pandas as pd
from qtpy.QtWidgets import (
    QComboBox, QDateEdit, QDateTimeEdit, QTextEdit, QSpinBox, QLineEdit,
    QDoubleSpinBox)

# ---- Local imports
from sardes.config.locale import _
from sardes.api.tabledelegates import SardesItemDelegate


# =============================================================================
# ---- Complex Delegates
# =============================================================================
class ObsWellIdEditDelegate(SardesItemDelegate):
    """
    A delegate to select an observation well from the list of existing well
    in the database.
    """

    # ---- SardesItemDelegate API
    def create_editor(self, parent):
        editor = QComboBox(parent)

        # Populate the combobox with the existing observation wells.
        obs_well_data = (self.model().libraries['observation_wells_data']
                         .sort_values('obs_well_id', axis=0, ascending=True))
        for index, values in obs_well_data.iterrows():
            editor.addItem(values['obs_well_id'], userData=index)

        return editor

    def format_data(self, data):
        isnull1 = data.isnull()
        try:
            obs_wells = (
                self.model().libraries['observation_wells_data'])
            obs_wells_dict = (
                obs_wells['obs_well_id']
                [obs_wells['obs_well_id'].isin(data)]
                .drop_duplicates()
                .reset_index()
                .set_index('obs_well_id')
                .to_dict()['sampling_feature_uuid'])
        except KeyError:
            obs_wells_dict = {}
        else:
            formatted_data = data.map(obs_wells_dict.get)
            isnull2 = formatted_data.isnull()
            if sum(isnull1 != isnull2):
                warning_message = _(
                    "Some {} data did not match any well in the database"
                    ).format(self.model().column_header_at(data.name))
            else:
                warning_message = None
        return formatted_data, warning_message


class SondeModelEditDelegate(SardesItemDelegate):
    """
    A delegate to select the brand of a sonde from a predefined list.
    """

    def create_editor(self, parent):
        editor = QComboBox(parent)

        # Populate the combobox with the available brand in the library.
        sonde_models_lib = self.model().libraries['sonde_models_lib']
        sonde_models_lib = sonde_models_lib.sort_values(
            'sonde_brand_model', axis=0, ascending=True)
        for index, values in sonde_models_lib.iterrows():
            editor.addItem(values['sonde_brand_model'], userData=index)
        return editor


class SondesSelectionDelegate(SardesItemDelegate):
    """
    A delegate to select a level or baro logger from the inventory.
    """

    def create_editor(self, parent):
        editor = QComboBox(parent)

        # Populate the combobox with the existing sondes.
        try:
            sondes_data = self.model().libraries['sondes_data']
            sonde_models_lib = self.model().libraries['sonde_models_lib']
        except KeyError:
            pass
        else:
            sondes_data['sonde_brand_model'] = sonde_models_lib.loc[
                sondes_data['sonde_model_id']]['sonde_brand_model'].values
            sondes_data['sonde_brand_model_serial'] = (
                sondes_data[['sonde_brand_model', 'sonde_serial_no']]
                .apply(lambda x: ' - '.join(x), axis=1))
            sondes_data = sondes_data.sort_values(
                'sonde_brand_model_serial', axis=0, ascending=True)
            for index, values in sondes_data.iterrows():
                editor.addItem(
                    values['sonde_brand_model_serial'], userData=index)
        return editor
