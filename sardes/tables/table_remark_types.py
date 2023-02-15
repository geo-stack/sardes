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


class RemarkTypesTableModel(StandardSardesTableModel):
    """
    A table model to display a list of remark types that
    are available to use in the Remarks table.
    """
    __tablename__ = 'remark_types'
    __tabletitle__ = _('Remark Types')
    __tablecolumns__ = [
        SardesTableColumn(
            'remark_type_code', _('Code'), 'str', notnull=True,
            unique=True),
        SardesTableColumn(
            'remark_type_name', _('Name'), 'str', notnull=True,
            unique=True),
        SardesTableColumn(
            'remark_type_desc', _('Description'), 'str', notnull=False,
            unique=False),
        ]

    __dataname__ = 'remark_types'
    __libnames__ = []

    # ---- SardesTableModel Public API
    def create_delegate_for_column(self, view, column):
        return TextEditDelegate(view, is_required=True)


class RemarkTypesTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = RemarkTypesTableModel()
        super().__init__(table_model, *args, **kargs)
