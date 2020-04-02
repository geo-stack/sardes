# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Third party imports
from qtpy.QtWidgets import QComboBox

# ---- Local imports
from sardes.widgets.tableviews import SardesItemDelegate


class ObsWellIdEditDelegate(SardesItemDelegate):
    """
    A delegate to select an obsercation well from the list of existing well
    in the database.
    """

    def create_editor(self, parent):
        editor = QComboBox(parent)

        # Populate the combobox with the existing observation wells.
        obs_well_data = (self.model().libraries['observation_wells_data']
                         .sort_values('obs_well_id', axis=0, ascending=True))
        for index in obs_well_data.index:
            editor.addItem(obs_well_data.loc[index, 'obs_well_id'],
                           userData=index)
        return editor


class SondeModelEditDelegate(SardesItemDelegate):
    """
    A delegate to select the brand of a sonde from a predefined list.
    """

    def create_editor(self, parent):
        editor = QComboBox(parent)

        # Populate the combobox with the available brand in the library.
        sonde_models_lib = self.model().libraries['sonde_models_lib']
        for index in sonde_models_lib.index:
            editor.addItem(sonde_models_lib.loc[index, 'sonde_brand_model'],
                           userData=index)
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
            for index in sondes_data.index:
                editor.addItem(
                    sondes_data.loc[index, 'sonde_brand_model_serial'],
                    userData=index)
        return editor
