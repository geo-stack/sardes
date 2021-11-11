# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the figures.py module.
"""

# ---- Third party imports
import matplotlib.pyplot as plt
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QMainWindow

# ---- Local imports
from sardes.api.figures import SardesFigureWidget, SardesFigureCanvas


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def figwidget(qtbot):
    figure, ax = plt.subplots(1, 1)
    ax.plot([1, 2, 3], [1, 2, 3], '.')

    figcanvas = SardesFigureCanvas(figure)
    figwidget = SardesFigureWidget(figcanvas)

    qtbot.addWidget(figwidget)
    figwidget.show()
    qtbot.waitExposed(figwidget)

    return figwidget

