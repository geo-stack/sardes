# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Local imports
from sardes.api.tablemodels import StandardSardesTableModel, SardesTableColumn
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
    __tablename__ = 'table_sondes_inventory'
    __tabletitle__ = _('Sondes Inventory')
    __tablecolumns__ = [
        SardesTableColumn('sonde_model_id', _('Model'), 'str',
                          notnull=True, unique=True,
                          unique_subset=['sonde_serial_no']),
        SardesTableColumn('sonde_serial_no', _('Serial Number'), 'str',
                          notnull=True, unique=True,
                          unique_subset=['sonde_model_id']),
        SardesTableColumn('date_reception', _('Date Reception'),
                          'datetime64[ns]'),
        SardesTableColumn('date_withdrawal', _('Date Withdrawal'),
                          'datetime64[ns]'),
        SardesTableColumn('in_repair', _('In Repair'), 'boolean',
                          notnull=True),
        SardesTableColumn('out_of_order', _('Out of order'), 'boolean',
                          notnull=True),
        SardesTableColumn('lost', _('Lost'), 'boolean',
                          notnull=True),
        SardesTableColumn('off_network', _('Off Network'), 'boolean',
                          notnull=True),
        SardesTableColumn('sonde_notes', _('Notes'), 'boolean')
        ]

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
        table_model = SondesInventoryTableModel()
        super().__init__(table_model, *args, **kargs)
