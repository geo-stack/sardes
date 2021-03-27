# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the tools.py module.
"""

# ---- Standard imports
import os.path as osp

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
    qtbot.waitForWindowShown(mainwindow)

    return mainwindow


# =============================================================================
# ---- Tests
# =============================================================================
def test_sardes_tool_visibility(mainwindow, qtbot):
    """Test that the dropdown menu button is initialized correctly."""
    tool = mainwindow.tool
    assert tool.toolbutton().isVisible()
    assert not tool.toolwidget().isVisible()

    # Show the tool.
    qtbot.mouseClick(tool.toolbutton(), Qt.LeftButton)
    qtbot.waitForWindowShown(tool.toolwidget())
    assert tool.toolwidget().isVisible()

    # Assert that the toolwidget is closed when the mainwindow is closed.
    mainwindow.close()
    assert not mainwindow.isVisible()
    assert not tool.toolwidget().isVisible()


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
