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
from sardes.api.tablemodels import SardesTableModel
from sardes.config.locale import _
from sardes.widgets.tableviews import (
    SardesItemDelegate, SardesTableWidget, StringEditDelegate,
    BoolEditDelegate, NotEditableDelegate, TextEditDelegate, DateTimeDelegate,
    NumEditDelegate)
from sardes.plugins.tables.tables.delegates import (
    ObsWellIdEditDelegate, SondesSelectionDelegate)


class SondeInstallationsTableModel(SardesTableModel):
    """
    A table model to display the list of sondes currently installed or
    that were installed at some point in the observation wells for the
    entire monitoring network.
    """

    def create_delegate_for_column(self, view, column):
        """
        Create the item delegate that the view need to use when editing the
        data of this model for the specified column. If None is returned,
        the items of the column will not be editable.
        """
        if column in ['sampling_feature_uuid']:
            return ObsWellIdEditDelegate(view, is_required=True)
        elif column == 'install_depth':
            return NumEditDelegate(view, decimals=3, bottom=-99999, top=99999)
        elif column in ['start_date']:
            return DateTimeDelegate(view, is_required=True,
                                    display_format="yyyy-MM-dd hh:mm")
        elif column in ['end_date']:
            return DateTimeDelegate(view, display_format="yyyy-MM-dd hh:mm")
        elif column in ['sonde_uuid']:
            return SondesSelectionDelegate(view)
        else:
            return NotEditableDelegate(view)

    # ---- Visual Data
    def logical_to_visual_data(self, visual_dataf):
        """
        Transform logical data to visual data.
        """
        try:
            obs_wells_data = self.libraries['observation_wells_data']
            visual_dataf['sampling_feature_uuid'] = (
                visual_dataf['sampling_feature_uuid']
                .replace(obs_wells_data['obs_well_id'].to_dict())
                )
        except KeyError:
            pass

        try:
            sondes_data = self.libraries['sondes_data']
            sonde_models_lib = self.libraries['sonde_models_lib']
            sondes_data['sonde_brand_model'] = sonde_models_lib.loc[
                sondes_data['sonde_model_id']]['sonde_brand_model'].values
            sondes_data['sonde_brand_model_serial'] = (
                sondes_data[['sonde_brand_model', 'sonde_serial_no']]
                .apply(lambda x: ' - '.join(x), axis=1))
            visual_dataf['sonde_uuid'] = (
                visual_dataf['sonde_uuid']
                .replace(sondes_data['sonde_brand_model_serial'].to_dict())
                )
        except KeyError:
            pass

        visual_dataf['start_date'] = (visual_dataf['start_date']
                                      .dt.strftime('%Y-%m-%d %H:%M'))
        visual_dataf['end_date'] = (visual_dataf['end_date']
                                    .dt.strftime('%Y-%m-%d %H:%M'))

        return visual_dataf


class SondeInstallationsTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = SondeInstallationsTableModel(
            table_title=_('Sonde Installations'),
            table_id='table_sonde_installations',
            data_columns_mapper=[
                ('sampling_feature_uuid', _('Well')),
                ('sonde_uuid', _('Brand Model Serial')),
                ('start_date', _('Date From')),
                ('end_date', _('Date To')),
                ('install_depth', _('Depth (m)'))]
            )
        super().__init__(table_model, *args, **kargs)
