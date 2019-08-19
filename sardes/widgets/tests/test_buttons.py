# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the ObservationWellTableView.
"""

# ---- Standard imports
import os.path as osp

# ---- Third party imports
import pytest
from qtpy.QtGui import QWheelEvent
from qtpy.QtCore import Qt, QSize, QPoint, QPointF

# ---- Local imports
from sardes.config.gui import get_iconsize
from sardes.widgets.buttons import DropdownToolButton

ACTIONS = ['Action #{}'.format(i) for i in range(3)]
ACTION_STATES = [True, False, False]


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dropdownbutton(qtbot):
    button = DropdownToolButton('checklist', get_iconsize())
    for action, state in zip(ACTIONS, ACTION_STATES):
        action = button.create_action(action, 'Data of {}'.format(action))
        action.setEnabled(state)
    qtbot.addWidget(button)
    button.show()
    return button


# =============================================================================
# ---- Tests for the DropdownToolButton
# =============================================================================
def test_dropdown_button_init(dropdownbutton):
    """Test that the dropdown menu button is initialized correctly."""
    assert len(dropdownbutton.menu().actions()) == len(ACTIONS)
    for i, action in enumerate(dropdownbutton.menu().actions()):
        assert action.text() == ACTIONS[i]
    assert dropdownbutton.checked_action().text() == ACTIONS[-1]
    assert dropdownbutton.text() == ACTIONS[-1]
    assert dropdownbutton.iconSize() == QSize(get_iconsize(), get_iconsize())


def test_dropdown_button_mousewheel(dropdownbutton, qtbot):
    """
    Test that the items from the button's dropdown menu are circled
    through correctly when rolling the wheel of the mouse over the button.
    """
    actions_index = len(ACTIONS) - 1
    assert dropdownbutton.checked_action().text() == ACTIONS[actions_index]
    for delta in [1, -1, -1, 1, 1, 1]:
        wheel_event = QWheelEvent(
            QPointF(dropdownbutton.pos()),
            QPointF(dropdownbutton.mapToGlobal(dropdownbutton.pos())),
            QPoint(0, delta),
            QPoint(0, delta),
            delta,
            Qt.Vertical,
            Qt.MidButton,
            Qt.NoModifier
            )
        with qtbot.waitSignal(dropdownbutton.sig_checked_action_changed):
            dropdownbutton.wheelEvent(wheel_event)

        actions_index += delta
        actions_index = 0 if actions_index == len(ACTIONS) else actions_index
        actions_index = (
            (len(ACTIONS) - 1) if actions_index < 0 else actions_index)
        assert dropdownbutton.checked_action().text() == ACTIONS[actions_index]


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw', '-s'])
