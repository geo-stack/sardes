# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Local imports
from sardes.api.plugins import SardesPlugin
from sardes.config.icons import get_icon
from sardes.config.locale import _
from sardes.plugins.tables.tables import (
    ObsWellsTableWidget, RepereTableWidget, SondesInventoryTableWidget,
    ManualMeasurementsTableWidget, SondeInstallationsTableWidget)

# ---- Third party imports
import pandas as pd
from qtpy.QtCore import Qt, QSize, Slot
from qtpy.QtWidgets import (QApplication, QFileDialog, QTabWidget,
                            QLabel, QFrame, QGridLayout, QWidget,
                            QPushButton, QToolButton, QStyle)

# ---- Local imports
from sardes.api.tablemodels import SardesTableModel
from sardes.api.timeseries import DataType, merge_timeseries_groups
from sardes.config.main import CONF
from sardes.widgets.tableviews import (
    SardesTableWidget, StringEditDelegate, BoolEditDelegate,
    NumEditDelegate, NotEditableDelegate, TextEditDelegate)


"""Readings plugin"""


class Readings(SardesPlugin):

    CONF_SECTION = 'readings'

    def __init__(self, parent):
        super().__init__(parent)
