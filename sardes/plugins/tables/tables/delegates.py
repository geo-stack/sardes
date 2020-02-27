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

