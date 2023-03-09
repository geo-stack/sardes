# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Local imports
from sardes.api.tablemodels import (
    SardesTableColumn, sardes_table_column_factory)
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
        SardesTableColumn(
            'survey_well_id', _('Well ID'), 'str',
            delegate=StringEditDelegate),
        sardes_table_column_factory(
            'hg_field_measurements', 'hg_survey_id',
            _('Survey Date/Time'),
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
                'decimals': 3, 'minimum': 0, 'maximum': 99999}),
        sardes_table_column_factory(
            'hg_field_measurements', 'meas_units_id', _('Units'),
            delegate=IntEditDelegate
            ),
        ]

    __dataname__ = 'hg_field_measurements'
    __libnames__ = ['measurement_units', 'hg_params', 'hg_surveys']


class HGFieldMeasurementsTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = HGFieldMeasurementsTableModel()
        super().__init__(table_model, *args, **kargs)
