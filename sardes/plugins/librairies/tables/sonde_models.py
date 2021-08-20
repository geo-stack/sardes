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
from sardes.widgets.tableviews import SardesTableWidget, TextEditDelegate


class SondeModelsTableModel(StandardSardesTableModel):
    """
    A table model to display a list of sonde brand models that
    are available to use in the SondesInventory table.
    """
    __tablecolumns__ = [
        SardesTableColumn(
            'sonde_brand', _('Brand'), 'str', notnull=True),
        SardesTableColumn(
            'sonde_model', _('Model'), 'str', notnull=True)
        ]

    # ---- SardesTableModel Public API
    def create_delegate_for_column(self, view, column):
        return TextEditDelegate(view, is_required=True)


class SondeModelsTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = SondeModelsTableModel(
            table_title=_('Sonde Models'),
            table_id='sonde_brand_models')
        super().__init__(table_model, *args, **kargs)
