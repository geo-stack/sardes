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
import os.path as osp

# ---- Third party imports
from appconfigs.base import get_home_dir
from qtpy.QtCore import Qt, QEvent, QObject, QSize, Signal, Slot
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (
    QAbstractButton, QAction, QActionGroup, QApplication, QMenu, QSizePolicy,
    QStyle, QStyleOptionToolButton, QStylePainter, QToolBar, QToolButton,
    QCheckBox, QFrame, QLineEdit, QLabel, QFileDialog, QPushButton,
    QGridLayout)

# ---- Local imports
from sardes.config.icons import get_icon
from sardes.config.gui import get_iconsize
from sardes.config.locale import _
from sardes.utils.qthelpers import create_action


class PathBoxWidget(QFrame):
    """
    A widget to display and select a directory or file location.
    """

    def __init__(self, parent=None, path='', workdir='', path_type='dir'):
        super().__init__(parent)
        self._workdir = workdir
        self._path_type = path_type

        self.browse_btn = QPushButton(_("Browse..."))
        self.browse_btn.setDefault(False)
        self.browse_btn.setAutoDefault(False)
        self.browse_btn.clicked.connect(self.browse_path)

        self.path_lineedit = QLineEdit()
        self.path_lineedit.setText(path)
        self.path_lineedit.setToolTip(path)
        self.path_lineedit.setFixedHeight(
            self.browse_btn.sizeHint().height() - 2)

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.path_lineedit, 0, 0)
        layout.addWidget(self.browse_btn, 0, 1)

    def is_valid(self):
        """Return whether path is valid."""
        return osp.exists(self.path())

    def is_empty(self):
        """Return whether the path is empty."""
        return self.path_lineedit.text() == ''

    def path(self):
        """Return the path of this pathbox widget."""
        return self.path_lineedit.text()

    def set_path(self, path):
        """Set the path to the specified value."""
        return self.path_lineedit.setText(path)

    def browse_path(self):
        """Open a dialog to select a new directory."""
        dialog_title = _('Modify Location')
        if self._path_type == 'dir':
            path = QFileDialog.getExistingDirectory(
                self, dialog_title, self.workdir(),
                options=QFileDialog.ShowDirsOnly)
        elif self._path_type == 'folder':
            path, ext = QFileDialog.getOpenFileName(
                self, dialog_title, self.workdir(),)
        if path:
            self.set_workdir(osp.dirname(path))
            self.path_lineedit.setText(path)
            self.path_lineedit.setToolTip(path)

    def workdir(self):
        """Return the directory that is used by the QFileDialog."""
        return self._workdir if osp.exists(self._workdir) else get_home_dir()

    def set_workdir(self, new_workdir):
        """Set the default directory that will be used by the QFileDialog."""
        if new_workdir is not None and osp.exists(new_workdir):
            self._workdir = new_workdir


class CheckboxPathBoxWidget(QFrame):
    """
    A widget to display and select a directory or file location, with
    a checkbox to enable or disable the widget and a group label.
    """

    def __init__(self, parent=None, label='', path='',
                 is_enabled=True, workdir=''):
        super().__init__(parent)
        self.label = label

        self.pathbox_widget = PathBoxWidget(parent=self, workdir=workdir)

        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(
            lambda _: self.pathbox_widget.setEnabled(self.is_enabled()))
        self.checkbox.setChecked(is_enabled)

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.checkbox, 0, 0)
        layout.addWidget(QLabel(label + ' :' if label else label), 0, 1)
        layout.addWidget(self.pathbox_widget, 1, 1)

    def is_enabled(self):
        """Return whether this pathbox widget is enabled or not."""
        return self.checkbox.isChecked()

    # ---- PathBoxWidget public API
    def is_valid(self):
        return self.pathbox_widget.is_valid()

    def is_empty(self):
        return self.pathbox_widget.is_empty()

    def path(self):
        return self.pathbox_widget.path()

    def set_path(self, path):
        return self.pathbox_widget.set_path(path)

    def browse_path(self):
        return self.pathbox_widget.browse_path()

    def workdir(self):
        return self.pathbox_widget.workdir()

    def set_workdir(self, new_workdir):
        return self.pathbox_widget.set_workdir(new_workdir)


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
