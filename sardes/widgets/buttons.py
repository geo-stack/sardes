# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard library imports
import sys

# ---- Third party imports
from qtpy.QtCore import Qt, QEvent, QObject, QSize, Signal, Slot
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (
    QAbstractButton, QAction, QActionGroup, QApplication, QMenu, QSizePolicy,
    QStyle, QStyleOptionToolButton, QStylePainter, QToolBar, QToolButton)

# ---- Local imports
from sardes.config.icons import get_icon
from sardes.config.gui import get_iconsize
from sardes.utils.qthelpers import create_action


class DropdownToolButton(QToolButton):
    """
    A toolbutton with a dropdown menu that acts like a combobox, but keeps the
    style of a toolbutton.
    """
    sig_checked_action_changed = Signal(QAction)

    def __init__(self, icon, iconsize, parent=None):
        super().__init__(parent)
        self.setIcon(get_icon(icon))
        self.setIconSize(QSize(iconsize, iconsize))
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self.setMenu(QMenu(self))
        self.setPopupMode(self.InstantPopup)
        self.menu().installEventFilter(self)

        policy = self.sizePolicy()
        policy.setVerticalPolicy(QSizePolicy.Expanding)
        self.setSizePolicy(policy)

        self._action_group = QActionGroup(self)

    def eventFilter(self, widget, event):
        """
        An event filter to make disabled menu items checkables.
        """
        if event.type() == QEvent.MouseButtonRelease and widget == self.menu():
            clicked_action = widget.actionAt(event.pos())
            if clicked_action is not None:
                clicked_action.setChecked(True)
                self.menu().close()
                event.accept()
        return super().eventFilter(widget, event)

    def create_action(self, name, data):
        """
        Create and add a new action to this button's menu.
        """
        action = create_action(self.action_group(),
                               name,
                               toggled=self._handle_checked_action_changed,
                               data=data)
        self.menu().addAction(action)
        action.setChecked(True)
        return action

    def action_group(self):
        """
        Return the action group of this button.
        """
        return self._action_group

    def checked_action(self):
        """
        Return the currently checked action of this button's menu.
        """
        return self._action_group.checkedAction()

    def wheelEvent(self, event):
        """
        Override Qt method to circle throuh the menu items of this button
        when the user roll the wheel of his mouse.
        """
        checked_action = self.checked_action()
        actions = self.menu().actions()
        for index, action in enumerate(actions):
            if action == checked_action:
                break
        if event.angleDelta().y() < 0:
            index = index - 1 if index > 0 else (len(actions) - 1)
        else:
            index = index + 1 if index < (len(actions) - 1) else 0
        actions[index].setChecked(True)
        return super().wheelEvent(event)

    def _handle_checked_action_changed(self, toggle):
        """
        Set the text of this button to that of the currently selected action.
        """
        if toggle:
            self.setText(self.checked_action().text() if
                         self.checked_action() else '')
            self.sig_checked_action_changed.emit(self.checked_action())

    def paintEvent(self, event):
        """
        Override Qt method to align the icon and text to the left.
        """
        sp = QStylePainter(self)
        opt = QStyleOptionToolButton()
        self.initStyleOption(opt)

        # Draw background.
        opt.text = ''
        opt.icon = QIcon()
        sp.drawComplexControl(QStyle.CC_ToolButton, opt)

        # Draw icon.
        sp.drawItemPixmap(opt.rect,
                          Qt.AlignLeft | Qt.AlignVCenter,
                          self.icon().pixmap(self.iconSize()))

        # Draw text.
        opt.rect.translate(self.iconSize().width() + 3, 0)
        sp.drawItemText(opt.rect,
                        Qt.AlignLeft | Qt.AlignVCenter,
                        self.palette(),
                        True,
                        self.text())


class SemiExclusiveButtonGroup(QObject):
    """
    The SemiExclusiveButtonGroup class provides an abstract  container to
    organize groups of button widgets. It does not provide a visual
    representation of this container, but instead manages the states of
    each of the buttons in the group.

    A SemiExclusiveButtonGroup button group switches off all checkable (toggle)
    buttons except the one that was clicked. Unlike the stock QButtonGroup of
    the Qt framework, the SemiExclusiveButtonGroup button group allow
    switching off the checked button by clicking on it.
    """

    def __init__(self):
        super().__init__()
        self.buttons = []

        # A reference to the last button that was toggled by the user, so that
        # its state can be restore programatically afterwards.
        self._last_toggled_button = None

        # A flag to indicate whether the buttons of this group are enabled
        # or not.
        self._is_enabled = True

    def add_button(self, button):
        """
        Add a new checkable button to this group.
        """
        self.buttons.append(button)
        button.toggled.connect(
            lambda checked: self._handle_button_toggled(button, checked))

    def set_enabled(self, state):
        """
        Enabled or disabled all the buttons of this group following the value
        of state.

        Parameters
        ----------
        state: bool
            A state value that indicates whether to enable or disable
            the buttons of this group.
        """
        self._is_enabled = state
        for button in self.buttons:
            button.setEnabled(state)

    def get_checked_button(self):
        """
        Return the button from this group that is currently checked or return
        None if no button is currently checked.
        """
        for button in self.buttons:
            if button.isChecked():
                return button
        else:
            return None

    def toggle_off(self):
        """
        Toggle off all buttons of this group.
        """
        for button in self.buttons:
            button.setChecked(False)

    def restore_last_toggled(self):
        """
        Check back the last button that was toggled by the user.
        """
        if self._last_toggled_button is not None and self._is_enabled:
            self._last_toggled_button.setChecked(True)

    @Slot(QAbstractButton, bool)
    def _handle_button_toggled(self, toggled_button, checked):
        """
        Handle when a button is toggled by switching off all checkable button
        but the one that was clicked. This button is toggle off if it was
        already checked.
        """
        if checked is True:
            self._last_toggled_button = toggled_button
            for button in self.buttons:
                if button != toggled_button:
                    button.setChecked(False)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    button = DropdownToolButton('checklist', get_iconsize())
    for i in range(3):
        button.create_action('Action #{}'.format(i),
                             'Data of Action #{}'.format(i))

    button.sig_checked_action_changed.connect(
        lambda action: print('{} toggled'.format(action.text()))
        )

    toolbar = QToolBar()
    toolbar.addWidget(button)
    toolbar.show()

    sys.exit(app.exec_())
