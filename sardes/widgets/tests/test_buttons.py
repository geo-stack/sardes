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


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dropdownbutton(qtbot):
    button = DropdownToolButton('checklist', get_iconsize())
    for action in ACTIONS:
        action = button.create_action(action, 'Data of {}'.format(action))
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


def test_mouseclick_disabled_action(dropdownbutton, qtbot):
    """
    Test that clicking on a disabled action with the mouse make this action
    the new currently checked action.
    """
    # Disable the second action of the menu.
    actions_index = 1
    assert actions_index != len(ACTIONS) - 1

    # Assert the checked action is still the last action added to the menu.
    dropdownbutton.menu().actions()[actions_index].setEnabled(False)
    assert dropdownbutton.checked_action().text() == ACTIONS[len(ACTIONS) - 1]

    # Click on the action that was just disabled and assert that this action
    # becomes the checked action afterwards.
    menu = dropdownbutton.menu()
    menu.show()

    action = menu.actions()[actions_index]
    with qtbot.waitSignal(dropdownbutton.sig_checked_action_changed):
        qtbot.mouseClick(
            menu,
            Qt.LeftButton,
            pos=menu.actionGeometry(action).center())
    assert dropdownbutton.checked_action().text() == ACTIONS[actions_index]


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw', '-s'])
