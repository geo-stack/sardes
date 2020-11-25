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
from qtpy.QtCore import (
    Qt, QEvent, QObject, QSize, Signal, Slot, QRect, QPoint)
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (
    QAbstractButton, QAction, QActionGroup, QApplication, QMenu, QSizePolicy,
    QStyle, QStyleOptionToolButton, QStylePainter, QToolBar, QToolButton,
    QDialog, QPushButton, QDialogButtonBox, QWidget, QTabWidget,
    QVBoxLayout, QTabBar, QStylePainter, QStyleOptionTab, QStyle)

# ---- Local imports
from sardes.config.locale import _
from sardes.config.icons import get_icon
from sardes.config.gui import get_iconsize
from sardes.utils.qthelpers import create_action


class HorizontalTabBar(QTabBar):
    # https://www.manongdao.com/q-367474.html

    def tabSizeHint(self, index):
        s = QTabBar.tabSizeHint(self, index)
        s.transpose()
        return s

    def paintEvent(self, event):
        painter = QStylePainter(self)
        opt = QStyleOptionTab()

        for i in range(self.count()):
            self.initStyleOption(opt, i)
            painter.drawControl(QStyle.CE_TabBarTabShape, opt)
            painter.save()

            s = opt.rect.size()
            s.transpose()
            r = QRect(QPoint(), s)
            r.moveCenter(opt.rect.center())
            opt.rect = r

            c = self.tabRect(i).center()
            painter.translate(c)
            painter.rotate(90)
            painter.translate(-c)
            painter.drawControl(QStyle.CE_TabBarTabLabel, opt)
            painter.restore()


class ConfDialog(QDialog):
    """
    A dialog window to manage Sardes preferences.
    """

    def __init__(self, main):
        super().__init__(main)
        self.main = main
        self.setWindowTitle(_('Preferences'))
        self.setWindowIcon(get_icon('preferences'))
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setModal(True)
        self.setMinimumHeight(500)

        self.confpages_tabwidget = QTabWidget()
        self.confpages_tabwidget.setTabBar(HorizontalTabBar())
        self.confpages_tabwidget.setTabPosition(QTabWidget.West)
        self._confpages = {}

        # Setup the dialog button box.
        self.ok_button = QPushButton(_('OK'))
        self.ok_button.setDefault(False)
        self.ok_button.setAutoDefault(False)
        self.apply_button = QPushButton(_('Apply'))
        self.apply_button.setDefault(True)
        self.cancel_button = QPushButton(_('Cancel'))
        self.cancel_button.setDefault(False)
        self.cancel_button.setAutoDefault(False)

        button_box = QDialogButtonBox()
        button_box.addButton(self.ok_button, button_box.ApplyRole)
        button_box.addButton(self.cancel_button, button_box.RejectRole)
        button_box.addButton(self.apply_button, button_box.ApplyRole)
        button_box.layout().insertSpacing(1, 100)
        button_box.clicked.connect(self._handle_button_click_event)

        # Setup the main layout.
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.confpages_tabwidget)
        main_layout.addWidget(button_box)
        main_layout.setStretch(0, 1)
        main_layout.setSizeConstraint(main_layout.SetFixedSize)

    def add_confpage(self, confpage):
        """Add confpage to this config dialog."""
        self._confpages[confpage.get_name()] = confpage
        self.confpages_tabwidget.addTab(
            confpage, confpage.get_icon(), confpage.get_label())

    @Slot(QAbstractButton)
    def _handle_button_click_event(self, button):
        """
        Handle when a button is clicked on the dialog button box.
        """
        if button == self.cancel_button:
            for confpage in self._confpages.values():
                confpage.load_from_conf()
            self.close()
        elif button == self.apply_button:
            for confpage in self._confpages.values():
                confpage.apply_changes()
        elif button == self.ok_button:
            for confpage in self._confpages.values():
                confpage.apply_changes()
            self.close()

