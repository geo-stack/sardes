# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sardes.tables.models import StandardSardesTableModel
    from sardes.plugins.hydrogeochemistry.plugin import Hydrogeochemistry

# ---- Standard imports
import datetime
import os.path as osp
import re

# ---- Third party imports
import pandas as pd
import openpyxl
from qtpy.QtCore import Qt, Signal, QObject
from qtpy.QtWidgets import QLabel, QApplication

# ---- Local imports
from sardes.config.icons import get_icon
from sardes.config.locale import _
from sardes.widgets.statusbar import ProcessStatusBar
from sardes.widgets.dialogs import UserMessageDialogBase
from sardes.utils.qthelpers import format_tooltip
from sardes.utils.qthelpers import create_toolbutton
from sardes.widgets.path import PathBoxWidget
from sardes.database.accessors.accessor_errors import ImportHGSurveysError
from sardes.api.tools import SardesTool


class HGLaboImportTool(SardesTool):
    def __init__(self, table):
        super().__init__(
            table,
            name='import_hglabo_report_tool',
            text=_("Import HG Lab Report"),
            icon='import_geochemistry',
            tip=_("Import HG data from an Excel lab report.")
            )

