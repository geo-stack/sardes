# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the SardesTableData class.
"""

# ---- Third party imports
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QToolBar, QMainWindow

# ---- Local imports
from sardes.api.tools import SardesToolExample


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def mainwindow(qtbot):
    toolbar = QToolBar()

    mainwindow = QMainWindow()
    mainwindow.addToolBar(toolbar)

    tool = SardesToolExample(parent=mainwindow)
    toolbar.addWidget(tool.toolbutton())
    mainwindow.tool = tool

    qtbot.addWidget(mainwindow)
    mainwindow.show()
    qtbot.waitExposed(mainwindow)

    return mainwindow



if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
