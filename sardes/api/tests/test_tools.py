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


# =============================================================================
# ---- Tests
# =============================================================================
def test_sardes_tool_visibility(mainwindow, qtbot):
    """Test that the dropdown menu button is initialized correctly."""
    tool = mainwindow.tool
    assert tool.toolbutton().isVisible()
    assert tool.toolwidget() is None

    # Show the tool.
    qtbot.mouseClick(tool.toolbutton(), Qt.LeftButton)
    qtbot.waitExposed(tool.toolwidget())
    assert tool.toolwidget().isVisible()

    # Assert that the toolwidget is closed when the mainwindow is closed.
    mainwindow.close()
    assert not mainwindow.isVisible()
    assert not tool.toolwidget().isVisible()


def test_toolwidget_window_title(mainwindow, qtbot):
    """Test that the title of the toolwidget is updated correctly.."""
    tool = mainwindow.tool
    tool.trigger()
    assert tool.toolwidget().isVisible()
    assert tool.toolwidget().windowTitle() == 'Sardes Tool Example'

    # Change the value of the SardesToolBase._text attribute, which is
    # used by default to set the title of the toolwidget window, and make sur
    # the title of the window is updated as expected.
    tool._text = 'Sardes Tool Example MODIF'
    tool.update()
    assert tool.toolwidget().windowTitle() == 'Sardes Tool Example MODIF'


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
