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


class HGParamsTableModel(StandardSardesTableModel):
    """
    A table model to display a list of pump types that
    are available to use in the HG Parameters table.
    """
    __tablename__ = 'table_hg_parameters'
    __tabletitle__ = _('HG Parameters')
    __tablecolumns__ = [
        sardes_table_column_factory(
            'hg_params', 'hg_param_code', _('Code'),
            delegate=StringEditDelegate),
        sardes_table_column_factory(
            'hg_params', 'hg_param_name', _('Name'),
            delegate=StringEditDelegate),
        sardes_table_column_factory(
            'hg_params', 'hg_param_regex', _('Regex'),
            delegate=StringEditDelegate),
        sardes_table_column_factory(
            'hg_params', 'cas_registry_number', _('CAS RN'),
            delegate=StringEditDelegate),
        ]

    __dataname__ = 'hg_params'
    __libnames__ = []


class HGParamsTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = HGParamsTableModel()
        super().__init__(table_model, *args, **kargs)
