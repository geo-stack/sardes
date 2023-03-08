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


class HGFieldMeasurementsTableModel(StandardSardesTableModel):
    """
    A table model to display the list of hydrogeochemical field measurements.
    """
    __tablename__ = 'table_hg_field_measurements'
    __tabletitle__ = _('HG Field Measurements')
    __tablecolumns__ = [
        sardes_table_column_factory(
            'hg_field_measurements', 'hg_survey_id', _('Survey'),
            delegate=StringEditDelegate),
        sardes_table_column_factory(
            'hg_field_measurements', 'hg_param_id', _('Parameter'),
            delegate=IntEditDelegate),
        sardes_table_column_factory(
            'hg_field_measurements', 'hg_param_value', _('Value'),
            delegate=StringEditDelegate),
        sardes_table_column_factory(
            'hg_field_measurements', 'lim_detection', _('Lim. Detection'),
            delegate=NumEditDelegate,
            delegate_options={
                'decimals': 3, 'minimum': 0, 'maximum': 99999})
        ]

    __dataname__ = 'hg_field_measurements'
    __libnames__ = ['hg_params', 'hg_surveys']


class HGFieldMeasurementsTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = HGFieldMeasurementsTableModel()
        super().__init__(table_model, *args, **kargs)
