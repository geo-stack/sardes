# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Third party imports
from qtpy.QtWidgets import QApplication, QStyle


ICON_COLOR = '#202020'
GREEN = '#00aa00'
RED = '#CC0000'


def get_iconsize():
    return 24


def get_layout_horizontal_spacing():
    """Return an integer value to use for layout horizontal spacing."""
    style = QApplication.instance().style()
    return style.pixelMetric(QStyle.PM_LayoutHorizontalSpacing)


def get_toolbar_item_spacing():
    """Return an integer value to use for toolbar items spacing."""
    style = QApplication.instance().style()
    return style.pixelMetric(QStyle.PM_ToolBarItemSpacing)
