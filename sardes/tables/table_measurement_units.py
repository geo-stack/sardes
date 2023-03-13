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


class MeasurementUnitsTableModel(StandardSardesTableModel):
    """
    A table model to display the list of measurement units that can
    be used to store various quantities in the BD.
    """
    __tablename__ = 'table_measurement_units'
    __tabletitle__ = _('Measurement Units')
    __tablecolumns__ = [
        sardes_table_column_factory(
            'measurement_units', 'meas_units_abb', _('Symbols'),
            delegate=StringEditDelegate),
        sardes_table_column_factory(
            'measurement_units', 'meas_units_name', _('Name'),
            delegate=StringEditDelegate),
        sardes_table_column_factory(
            'measurement_units', 'meas_units_desc', _('Description'),
            delegate=TextEditDelegate),
        ]

    __dataname__ = 'measurement_units'
    __libnames__ = []


class MeasurementUnitsTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = MeasurementUnitsTableModel()
        super().__init__(table_model, *args, **kargs)
