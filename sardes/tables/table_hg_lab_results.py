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
from sardes.tables.delegates import (
    StringEditDelegate, IntEditDelegate, NumEditDelegate)


class HGLabResultsTableModel(StandardSardesTableModel):
    """
    A table model to display the list of hydrogeochemical field measurements.
    """
    __tablename__ = 'table_hg_lab_results'
    __tabletitle__ = _('HG Lab Results')
    __tablecolumns__ = [
        sardes_table_column_factory(
            'hg_lab_results', 'lab_sample_id', _('Lab Sample ID'),
            delegate=StringEditDelegate),
        sardes_table_column_factory(
            'hg_lab_results', 'hg_param_id', _('Parameter'),
            delegate=IntEditDelegate),
        sardes_table_column_factory(
            'hg_lab_results', 'hg_param_value', _('Value'),
            delegate=StringEditDelegate),
        sardes_table_column_factory(
            'hg_lab_results', 'lim_detection', _('Lim. Detection'),
            delegate=NumEditDelegate,
            delegate_options={
                'decimals': 3, 'minimum': 0, 'maximum': 99999}),
        sardes_table_column_factory(
            'hg_lab_results', 'code_analysis_method', _('Method'),
            delegate=StringEditDelegate),
        ]

    __dataname__ = 'hg_lab_results'
    __libnames__ = []


class HGLabResultsTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = HGLabResultsTableModel()
        super().__init__(table_model, *args, **kargs)
