# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Local imports
from sardes.api.tablemodels import StandardSardesTableModel
from sardes.config.locale import _
from sardes.widgets.tableviews import (
    SardesTableWidget, StringEditDelegate, BoolEditDelegate,
    NotEditableDelegate, TextEditDelegate, DateEditDelegate)
from sardes.plugins.tables.tables.delegates import SondeModelEditDelegate


class SondesInventoryTableModel(StandardSardesTableModel):
    """
    A table model to display the list of level and baro loggers that are
    used in the monitoring network.
    """

    def create_delegate_for_column(self, view, column):
        """
        Create the item delegate that the view need to use when editing the
        data of this model for the specified column. If None is returned,
        the items of the column will not be editable.
        """
        if column in ['out_of_order', 'in_repair', 'lost', 'off_network']:
            return BoolEditDelegate(view, is_required=True)
        elif column in ['date_reception', 'date_withdrawal']:
            return DateEditDelegate(view)
        elif column == 'sonde_notes':
            return TextEditDelegate(view)
        elif column == 'sonde_serial_no':
            return StringEditDelegate(view)
        elif column == 'sonde_model_id':
            return SondeModelEditDelegate(view, is_required=True)
        else:
            return NotEditableDelegate(view)

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

        return visual_dataf


class SondesInventoryTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = SondesInventoryTableModel(
            table_title=_('Sondes Inventory'),
            table_id='table_sondes_inventory',
            data_columns_mapper=[
                ('sonde_model_id', _('Model')),
                ('sonde_serial_no', _('Serial Number')),
                ('date_reception', _('Date Reception')),
                ('date_withdrawal', _('Date Withdrawal')),
                ('in_repair', _('In Repair')),
                ('out_of_order', _('Out of order')),
                ('lost', _('Lost')),
                ('off_network', _('Off Network')),
                ('sonde_notes', _('Notes'))]
            )
        super().__init__(table_model, *args, **kargs)
