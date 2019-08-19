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
from qtpy.QtCore import Qt, QEvent, QSize
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (
    QActionGroup, QApplication, QMenu, QSizePolicy, QStyle,
    QStyleOptionToolButton, QStylePainter, QToolBar, QToolButton)

# ---- Local imports
from sardes.config.icons import get_icon
from sardes.config.gui import get_iconsize
from sardes.utils.qthelpers import create_action


class DropdownToolButton(QToolButton):
    """
    A toolbutton with a dropdown menu that acts like a combobox, but keeps the
    style of a toolbutton.
    """

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

    def create_action(self, name, toggled, data):
        """
        Create and add a new action to this button's menu.
        """
        action = create_action(self.action_group(),
                               name,
                               toggled=toggled,
                               data=data)
        action.toggled.connect(self._handle_checked_action_changed)
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


if __name__ == '__main__':
    app = QApplication(sys.argv)

    button = DropdownToolButton('checklist', get_iconsize())
    for i in range(3):
        button.create_action(
            'Action #{}'.format(i),
            lambda _, i=i: print('Action #{} toggled'.format(i)),
            'Data of Action #{}'.format(i))

    toolbar = QToolBar()
    toolbar.addWidget(button)
    toolbar.show()

    sys.exit(app.exec_())
