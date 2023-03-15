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


class HGSamplingMethodsTableModel(StandardSardesTableModel):
    """
    A table model to display a list of pump types that
    are available to use in the HG Sampling Methods table.
    """
    __tablename__ = 'table_hg_sampling_methods'
    __tabletitle__ = _('HG Sampling Methods')
    __tablecolumns__ = [
        sardes_table_column_factory(
            'hg_sampling_methods', 'hg_sampling_method_name', _('Name'),
            delegate=StringEditDelegate),
        sardes_table_column_factory(
            'hg_sampling_methods', 'hg_sampling_method_desc', _('Description'),
            delegate=StringEditDelegate),
        ]

    __dataname__ = 'hg_sampling_methods'
    __libnames__ = []


class HGSamplingMethodsTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = HGSamplingMethodsTableModel()
        super().__init__(table_model, *args, **kargs)
