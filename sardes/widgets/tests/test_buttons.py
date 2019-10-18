# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the buttons.py module.
"""

# ---- Standard imports
import os.path as osp

# ---- Third party imports
import pytest
from qtpy.QtGui import QWheelEvent
from qtpy.QtCore import Qt, QSize, QPoint
from qtpy.QtWidgets import QToolBar, QToolButton

# ---- Local imports
from sardes.config.gui import get_iconsize
from sardes.widgets.buttons import DropdownToolButton, SemiExclusiveButtonGroup

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


@pytest.fixture
def semiexclusive_buttongroup(qtbot):
    button1 = QToolButton()
    button1.setCheckable(True)
    button1.setObjectName('Button#1')

    button2 = QToolButton()
    button2.setCheckable(True)
    button2.setObjectName('Button#2')

    toolbar = QToolBar()
    toolbar.addWidget(button1)
    toolbar.addWidget(button2)
    qtbot.addWidget(toolbar)
    toolbar.show()

    button_group = SemiExclusiveButtonGroup()
    button_group.add_button(button1)
    button_group.add_button(button2)

    # We need to keep a reference to the toolbar or else it is garbage
    # collected.
    button_group.toolbar = toolbar

    return button_group


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
            dropdownbutton.pos(),
            dropdownbutton.mapToGlobal(dropdownbutton.pos()),
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


# =============================================================================
# ---- Tests for the SemiExclusiveButtonGroup
# =============================================================================
def test_semiexclusive_buttongroup_init(semiexclusive_buttongroup):
    """
    Test that the semi-exclusive abstract button group is
    initialized correctly.
    """
    assert semiexclusive_buttongroup.get_checked_button() is None
    assert semiexclusive_buttongroup._last_toggled_button is None
    assert len(semiexclusive_buttongroup.buttons) == 2


def test_semiexclusive_buttongroup_click(semiexclusive_buttongroup, qtbot):
    """
    Test that toggling on and off buttons in the group is working as
    expected.
    """
    # Click the first, then second button of the group.
    for i in range(2):
        qtbot.mouseClick(semiexclusive_buttongroup.buttons[i], Qt.LeftButton)
        assert semiexclusive_buttongroup.buttons[i].isChecked()
        assert (semiexclusive_buttongroup.get_checked_button() ==
                semiexclusive_buttongroup.buttons[i])
        assert (semiexclusive_buttongroup._last_toggled_button ==
                semiexclusive_buttongroup.buttons[i])

    # Click again the currently checked button.
    qtbot.mouseClick(semiexclusive_buttongroup.buttons[i], Qt.LeftButton)
    assert not semiexclusive_buttongroup.buttons[i].isChecked()
    assert semiexclusive_buttongroup.get_checked_button() is None
    assert (semiexclusive_buttongroup._last_toggled_button ==
            semiexclusive_buttongroup.buttons[i])


def test_semiexclusive_buttongroup_utils(semiexclusive_buttongroup, qtbot):
    """
    Test that the utility methods `toggle_off` and `restore_last_toggled` of
    the semi-exclusive button group work as expected.
    """
    # Click the first button of the group.
    qtbot.mouseClick(semiexclusive_buttongroup.buttons[0], Qt.LeftButton)
    assert (semiexclusive_buttongroup.get_checked_button() ==
            semiexclusive_buttongroup.buttons[0])

    # Toggle off the buttons.
    semiexclusive_buttongroup.toggle_off()
    assert semiexclusive_buttongroup.get_checked_button() is None

    # Toggle back the last button that was toggled.
    semiexclusive_buttongroup.restore_last_toggled()
    assert (semiexclusive_buttongroup.get_checked_button() ==
            semiexclusive_buttongroup.buttons[0])


def test_semiexclusive_buttongroup_enabled(semiexclusive_buttongroup, qtbot):
    """
    Test that the utility method `set_enable` of the semi-exclusive button
    group works as expected.
    """
    assert semiexclusive_buttongroup._is_enabled
    for button in semiexclusive_buttongroup.buttons:
        assert button.isEnabled()

    # Disable and enable consecutively the buttons of the semi-exclusive
    # button group.
    for state in [False, True]:
        semiexclusive_buttongroup.set_enabled(state)
        assert semiexclusive_buttongroup._is_enabled is state
        for button in semiexclusive_buttongroup.buttons:
            assert button.isEnabled() is state


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw', '-s'])
