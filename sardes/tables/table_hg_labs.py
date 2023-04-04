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
from sardes.tables.delegates import StringEditDelegate, TextEditDelegate


class HGLabsTableModel(StandardSardesTableModel):
    """
    A table model to display the list of labs that can analyze
    groundwater sample.
    """
    __tablename__ = 'table_hg_labs'
    __tabletitle__ = _('HG Labs')
    __tablecolumns__ = [
        sardes_table_column_factory(
            'hg_labs', 'lab_code', _('Code'),
            delegate=StringEditDelegate),
        sardes_table_column_factory(
            'hg_labs', 'lab_name', _('Name'),
            delegate=StringEditDelegate),
        sardes_table_column_factory(
            'hg_labs', 'lab_contacts', _('Contact Details'),
            delegate=TextEditDelegate),
        ]

    __dataname__ = 'hg_labs'
    __libnames__ = []


class HGLabsTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = HGLabsTableModel()
        super().__init__(table_model, *args, **kargs)
