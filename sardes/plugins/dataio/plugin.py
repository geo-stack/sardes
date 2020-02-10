# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports
import os.path as osp

# ---- Third party imports
from appconfigs.base import get_home_dir
import hydsensread as hsr
from qtpy.QtCore import Qt, QSize, Slot, Signal
from qtpy.QtWidgets import (QApplication, QFileDialog, QTabWidget,
                            QDialog, QGridLayout, QLabel, QPushButton,
                            QDialogButtonBox, QVBoxLayout, QAbstractButton,
                            QFormLayout)

# ---- Local imports
from sardes.config.main import CONF
from sardes.api.plugins import SardesPlugin
from sardes.api.tablemodels import SardesTableModel
from sardes.config.icons import get_icon
from sardes.config.locale import _
from sardes.utils.qthelpers import (
    create_mainwindow_toolbar, create_toolbutton)
from sardes.widgets.tableviews import NotEditableDelegate, SardesTableWidget


"""Data Input/Output plugin"""

