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
from sardes.widgets.tableviews import SardesTableWidget
from sardes.tables.delegates import TextEditDelegate, StringEditDelegate


class RemarkTypesTableModel(StandardSardesTableModel):
    """
    A table model to display a list of remark types that
    are available to use in the Remarks table.
    """
    __tablename__ = 'table_remark_types'
    __tabletitle__ = _('Remark Types')
    __tablecolumns__ = [
        SardesTableColumn(
            'remark_type_code', _('Code'), 'str',
            notnull=True, unique=True,
            delegate=StringEditDelegate),
        SardesTableColumn(
            'remark_type_name', _('Name'), 'str',
            notnull=True, unique=True,
            delegate=StringEditDelegate),
        SardesTableColumn(
            'remark_type_desc', _('Description'), 'str',
            delegate=TextEditDelegate),
        ]

    __dataname__ = 'remark_types'
    __libnames__ = []


class RemarkTypesTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = RemarkTypesTableModel()
        super().__init__(table_model, *args, **kargs)
