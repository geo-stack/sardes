# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard library imports
from enum import Enum

# ---- Local imports
from sardes.config.locale import _


class DataType(Enum):
    """
    This enum type describes the type of data constituing the time series.
    """
    WaterLevel = (0, 'blue', _("Water level"), _("Water Level"), 'm')
    WaterTemp = (1, 'red', _("Water temperature"), _("Temperature"), '\u00B0C')
    WaterEC = (2, 'cyan', _("Water electrical conductivity"),
               _("Conductivity"), 'µS/cm')

    def __new__(cls, *args, **kwds):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    def __init__(self, _: int, color: str, title: str, label: str,
                 units: str):
        self._color = color
        self._title = title
        self._label = label
        self._units = units

    @property
    def color(self):
        return self._color

    @property
    def title(self):
        return self._title

    @property
    def label(self):
        return self._label

    @property
    def units(self):
        """
        Return the SI units in which the data of this type are saved.
        """
        return self._units


if __name__ == '__main__':
    print(DataType.WaterLevel)
    print(DataType.WaterLevel.value)
    print(DataType.WaterLevel.name)
    print(DataType.WaterLevel.color)
    print(DataType.WaterLevel.label)
