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


class ToggleVisibilityMenu(QMenu):
    def mouseReleaseEvent(self, event):
        """
        Override Qt method to prevent menu from closing when an action
        is toggled.
        """
        action = self.activeAction()
        if action:
            action.setChecked(not action.isChecked())
        event.accept()


class ToggleVisibilityToolButton(QToolButton):
    sig_item_clicked = Signal(object, bool)

    def __init__(self, iconsize, parent=None):
        super().__init__(parent)
        self.setIcon(get_icon('eye_on'))
        self.setIconSize(QSize(iconsize, iconsize))

        self.setMenu(ToggleVisibilityMenu(self))
        self.setPopupMode(self.InstantPopup)
        self.menu().installEventFilter(self)

    def count(self):
        """
        Return the number of items in this ToggleVisibilityToolButton.
        """
        return len(self.menu().actions())

    def create_action(self, name, item):
        """
        Create and add a new action to this button's menu.
        """
        action = create_action(
            self, name,
            toggled=lambda toggle:
                self.sig_item_clicked.emit(item, toggle),
            data=item)
        self.menu().addAction(action)
        action.setChecked(True)
        self.setEnabled(self.count() > 0)
        return action

    def remove_action(self, item):
        """
        Remove the action corresponding to the given item from this
        toolbutton menu.
        """
        for action in self.menu().actions():
            if action.data() == item:
                self.menu().removeAction(action)
        if self.count() == 0:
            self.setEnabled(False)


class LeftAlignedToolButton(QToolButton):
    def paintEvent(self, event):
        """
        Override Qt method to align the icon and text to the left, else they
        are centered horiztonlly to the button width.
        """
        sp = QStylePainter(self)
        opt = QStyleOptionToolButton()
        self.initStyleOption(opt)

        # Draw background.
        opt.text = ''
        opt.icon = QIcon()
        sp.drawComplexControl(QStyle.CC_ToolButton, opt)

        # Draw icon.
        QStyle.PM_ButtonMargin
        sp.drawItemPixmap(opt.rect,
                          Qt.AlignLeft | Qt.AlignVCenter,
                          self.icon().pixmap(self.iconSize()))

        # Draw text.
        hspacing = QApplication.instance().style().pixelMetric(
            QStyle.PM_ButtonMargin)
        if not self.icon().isNull():
            hspacing += self.iconSize().width()
        opt.rect.translate(hspacing, 0)
        sp.drawItemText(opt.rect,
                        Qt.AlignLeft | Qt.AlignVCenter,
                        self.palette(),
                        True,
                        self.text())


class DropdownToolButton(LeftAlignedToolButton):
    """
    A toolbutton with a dropdown menu that acts like a combobox, but keeps the
    style of a toolbutton.
    """
    sig_checked_action_changed = Signal(QAction)

    def __init__(self, icon=None, iconsize=None, parent=None,
                 placeholder_text=''):
        super().__init__(parent)
        self._adjust_size_to_content = True
        self._placeholder_text = placeholder_text

        self.setMinimumWidth(100)
        if icon is not None:
            self.setIcon(get_icon(icon))
        if iconsize is not None:
            self.setIconSize(QSize(iconsize, iconsize))
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self.setMenu(QMenu(self))
        self.setPopupMode(self.InstantPopup)
        self.menu().installEventFilter(self)

        policy = self.sizePolicy()
        policy.setVerticalPolicy(QSizePolicy.Expanding)
        self.setSizePolicy(policy)

        self._action_group = QActionGroup(self)

        self.setEnabled(False)
        self.setText(self._placeholder_text)

    def count(self):
        """
        Return the number of items in this DropdownToolButton.
        """
        return len(self.menu().actions())

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
        self.setEnabled(self.count() > 0)
        return action

    def remove_action(self, data):
        """
        Remove the action corresponding to the given data.
        """
        for action in self.menu().actions():
            if action.data() == data:
                self.action_group().removeAction(action)
                self.menu().removeAction(action)
        if self.count() == 0:
            self.setEnabled(False)
            self.setText(self._placeholder_text)

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

    def setCheckedAction(self, index):
        """
        Set the currently checked action to the action located at the given
        index in the list.
        """
        self.action_group().actions()[index].setChecked(True)

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
                         self.checked_action() else self._placeholder_text)
            self.sig_checked_action_changed.emit(self.checked_action())
        if self._adjust_size_to_content and self.width() > self.minimumWidth():
            self.setMinimumWidth(self.width())


class SemiExclusiveButtonGroup(QObject):
    """
    The SemiExclusiveButtonGroup class provides an abstract container to
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

    visibility_btn = ToggleVisibilityToolButton(get_iconsize())
    visibility_btn.create_action('Item #1', object())
    visibility_btn.create_action('Item #2', object())
    visibility_btn.create_action('Item #3', object())

    button = DropdownToolButton('checklist', get_iconsize())
    for i in range(3):
        button.create_action('Item #{}'.format(i),
                             'Data of Action #{}'.format(i))
    button.sig_checked_action_changed.connect(
        lambda action: print('{} toggled'.format(action.text()))
        )

    toolbar = QToolBar()
    toolbar.addWidget(visibility_btn)
    toolbar.addWidget(button)
    toolbar.show()

    sys.exit(app.exec_())
