# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Local imports
from sardes.api.tablemodels import sardes_table_column_factory
from sardes.config.locale import _
from sardes.tables.models import StandardSardesTableModel
from sardes.widgets.tableviews import SardesTableWidget
from sardes.tables.delegates import StringEditDelegate


class PumpTypesTableModel(StandardSardesTableModel):
    """
    A table model to display a list of pump types that
    are available to use in the Purge table.
    """
    __tablename__ = 'table_pump_types'
    __tabletitle__ = _('Pump Types')
    __tablecolumns__ = [
        sardes_table_column_factory(
            'pump_types', 'pump_type_name', _('Name'),
            delegate=StringEditDelegate),
        sardes_table_column_factory(
            'pump_types', 'pump_type_desc', _('Description'),
            delegate=StringEditDelegate),
        ]

    __dataname__ = 'pump_types'
    __libnames__ = []


class PumpTypesTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = PumpTypesTableModel()
        super().__init__(table_model, *args, **kargs)
