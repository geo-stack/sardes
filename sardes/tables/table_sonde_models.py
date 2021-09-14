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
        SardesTableColumn(
            'sonde_brand', _('Brand'), 'str', notnull=True,
            unique=True, unique_subset=['sonde_model']),
        SardesTableColumn(
            'sonde_model', _('Model'), 'str', notnull=True,
            unique=True, unique_subset=['sonde_brand'])
        ]

    __dataname__ = 'sonde_models_lib'
    __libnames__ = []
    __foreignconstraints__ = [
        ('sonde_model_id', 'sondes_data')
        ]

    # ---- SardesTableModel Public API
    def create_delegate_for_column(self, view, column):
        return TextEditDelegate(view, is_required=True)


class SondeModelsTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = SondeModelsTableModel()
        super().__init__(table_model, *args, **kargs)
