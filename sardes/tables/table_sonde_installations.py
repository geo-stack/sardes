# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Local imports
from sardes.api.tablemodels import SardesTableColumn
from sardes.config.locale import _
from sardes.widgets.tableviews import SardesTableWidget
from sardes.tables.models import StandardSardesTableModel
from sardes.tables.delegates import (
    ObsWellIdEditDelegate, SondesSelectionDelegate, NotEditableDelegate,
    TextEditDelegate, DateTimeDelegate, NumEditDelegate)


class SondeInstallationsTableModel(StandardSardesTableModel):
    """
    A table model to display the list of sondes currently installed or
    that were installed at some point in the observation wells for the
    entire monitoring network.
    """
    __tablename__ = 'table_sonde_installations'
    __tabletitle__ = _('Sonde Installations')
    __tablecolumns__ = [
        SardesTableColumn(
            'sampling_feature_uuid', _('Well ID'), 'str', notnull=True,
            delegate=ObsWellIdEditDelegate),
        SardesTableColumn(
            'sonde_uuid', _('Brand Model Serial'), 'str', notnull=True,
            delegate=SondesSelectionDelegate),
        SardesTableColumn(
            'start_date', _('Date From'), 'datetime64[ns]', notnull=True,
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd hh:mm"}),
        SardesTableColumn(
            'end_date', _('Date To'), 'datetime64[ns]',
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd hh:mm"}),
        SardesTableColumn(
            'install_depth', _('Depth (m)'), 'float64', notnull=True,
            delegate=NumEditDelegate,
            delegate_options={
                'decimals': 3, 'minimum': -99999, 'maximum': 99999}),
        SardesTableColumn(
            'install_note', _('Notes'), 'str',
            delegate=TextEditDelegate)
        ]

    __dataname__ = 'sonde_installations'
    __tablelibs__ = ['observation_wells_data',
                     'sondes_data',
                     'sonde_models_lib']

    # ---- Visual Data
    def logical_to_visual_data(self, visual_dataf):
        """
        Transform logical data to visual data.
        """
        try:
            obs_wells_data = self.libraries['observation_wells_data']
            visual_dataf['sampling_feature_uuid'] = (
                visual_dataf['sampling_feature_uuid']
                .map(obs_wells_data['obs_well_id'].to_dict().get)
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
                .map(sondes_data['sonde_brand_model_serial'].to_dict().get)
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
        table_model = SondeInstallationsTableModel()
        super().__init__(table_model, *args, **kargs)
