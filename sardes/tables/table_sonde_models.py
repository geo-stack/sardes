# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sardes.widgets.tableviews import SardesTableView
    from sardes.api.tablemodels import SardesTableColumn


# ---- Local imports
from sardes.api.tablemodels import sardes_table_column_factory
from sardes.config.locale import _
from sardes.tables.models import StandardSardesTableModel
from sardes.tables.delegates import TextEditDelegate
from sardes.widgets.tableviews import SardesTableWidget


class SondeModelsTableModel(StandardSardesTableModel):
    """
    A table model to display a list of sonde brand models that
    are available to use in the SondesInventory table.
    """
    __tablename__ = 'sonde_brand_models'
    __tabletitle__ = _('Sonde Models')
    __tablecolumns__ = [
        sardes_table_column_factory(
            'sonde_models_lib', 'sonde_brand', _('Brand')),
        sardes_table_column_factory(
            'sonde_models_lib', 'sonde_model', _('Model'))
        ]

    __dataname__ = 'sonde_models_lib'
    __libnames__ = []

    # ---- SardesTableModel Public API
    def create_delegate_for_column(self, table_view: SardesTableView,
                                   table_column: SardesTableColumn):
        delegate = TextEditDelegate(table_view, table_column)
        self._column_delegates[table_column.name] = delegate
        return delegate


class SondeModelsTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = SondeModelsTableModel()
        super().__init__(table_model, *args, **kargs)
