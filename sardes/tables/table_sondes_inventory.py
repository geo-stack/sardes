# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Local imports
from sardes.api.tablemodels import (
    SardesTableColumn, sardes_table_column_factory)
from sardes.config.locale import _
from sardes.widgets.tableviews import SardesTableWidget
from sardes.tables.models import StandardSardesTableModel
from sardes.tables.delegates import (
    SondeModelEditDelegate, StringEditDelegate, BoolEditDelegate,
    TextEditDelegate, DateEditDelegate, DateTimeDelegate)


class SondesInventoryTableModel(StandardSardesTableModel):
    """
    A table model to display the list of level and baro loggers that are
    used in the monitoring network.
    """
    __tablename__ = 'table_sondes_inventory'
    __tabletitle__ = _('Sondes Inventory')
    __tablecolumns__ = [
        sardes_table_column_factory(
            'sondes_data', 'sonde_model_id', _('Model'),
            delegate=SondeModelEditDelegate),
        sardes_table_column_factory(
            'sondes_data', 'sonde_serial_no', _('Serial Number'),
            delegate=StringEditDelegate),
        sardes_table_column_factory(
            'sondes_data', 'date_reception', _('Date Reception'),
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd"},
            strftime_format='%Y-%m-%d'),
        sardes_table_column_factory(
            'sondes_data', 'date_withdrawal', _('Date Withdrawal'),
            delegate=DateTimeDelegate,
            delegate_options={'display_format': "yyyy-MM-dd"},
            strftime_format='%Y-%m-%d'),
        sardes_table_column_factory(
            'sondes_data', 'in_repair', _('In Repair'),
            delegate=BoolEditDelegate),
        sardes_table_column_factory(
            'sondes_data', 'out_of_order', _('Out of order'),
            delegate=BoolEditDelegate),
        sardes_table_column_factory(
            'sondes_data', 'lost', _('Lost'),
            delegate=BoolEditDelegate),
        sardes_table_column_factory(
            'sondes_data', 'off_network', _('Off Network'),
            delegate=BoolEditDelegate),
        sardes_table_column_factory(
            'sondes_data', 'sonde_notes', _('Notes'),
            delegate=TextEditDelegate)
        ]

    __dataname__ = 'sondes_data'
    __libnames__ = ['sonde_models_lib']

    # ---- Visual Data
    def logical_to_visual_data(self, visual_dataf):
        """
        Transform logical data to visual data.
        """
        try:
            sonde_models_lib = self.libraries['sonde_models_lib']
            visual_dataf['sonde_model_id'] = (
                visual_dataf['sonde_model_id']
                .map(sonde_models_lib['sonde_brand_model'].to_dict().get)
                )
        except KeyError:
            pass

        for column in ['out_of_order', 'in_repair', 'lost', 'off_network']:
            visual_dataf[column] = (
                visual_dataf[column]
                .map({True: _('Yes'), False: _('No')}.get)
                )

        return super().logical_to_visual_data(visual_dataf)


class SondesInventoryTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = SondesInventoryTableModel()
        super().__init__(table_model, *args, **kargs)
