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
    Qt, Signal, Slot, QRect, QPoint)
from qtpy.QtWidgets import (
    QAbstractButton, QAction, QActionGroup, QApplication, QMenu, QSizePolicy,
    QStyle, QStyleOptionToolButton, QStylePainter, QToolBar, QToolButton,
    QDialog, QPushButton, QDialogButtonBox, QWidget, QTabWidget,
    QVBoxLayout, QTabBar, QStylePainter, QStyleOptionTab, QStyle)

# ---- Local imports
from sardes.config.locale import _
from sardes.config.icons import get_icon


class HorizontalTabBar(QTabBar):
    """
    A custom tabbar to show tabs on the side, while keeping the text
    orientation horitontal.
    """
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
        self.apply_button.setEnabled(False)
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

    def count(self):
        "Return the number of configuration pages added to this dialog."
        return len(self._confpages)

    def get_confpage(self, confpage_name):
        """Return the confpage corresponding to the given name."""
        return self._confpages.get(confpage_name, None)

    def add_confpage(self, confpage):
        """Add confpage to this config dialog."""
        self._confpages[confpage.name()] = confpage
        self.confpages_tabwidget.addTab(
            confpage, confpage.icon(), confpage.label())
        confpage.sig_settings_changed.connect(
            self._handle_confpage_settings_changed)

    @Slot(QAbstractButton)
    def _handle_button_click_event(self, button):
        """
        Handle when a button is clicked on the dialog button box.
        """
        if button == self.cancel_button:
            self.close()
        elif button == self.apply_button:
            for confpage in self._confpages.values():
                confpage.apply_changes()
        elif button == self.ok_button:
            for confpage in self._confpages.values():
                confpage.apply_changes()
            self.close()
        self.apply_button.setEnabled(False)

    def closeEvent(self, event):
        """
        Override this QT to revert confpage settings to the value saved in
        the user configuration files.
        """
        for confpage in self._confpages.values():
            if confpage.is_modified():
                confpage.load_settings_from_conf()
        self.apply_button.setEnabled(False)
        super().closeEvent(event)

    def _handle_confpage_settings_changed(self):
        """
        Handle when the settings in one of the registered pages changed.
        """
        for confpage in self._confpages.values():
            if confpage.is_modified():
                self.apply_button.setEnabled(True)
                break
        else:
            self.apply_button.setEnabled(False)


class ConfPageBase(QWidget):
    """
    Basic functionality for Sardes configuration pages.

    WARNING: Don't override any methods or attributes present here unless you
    know what you are doing.
    """
    sig_settings_changed = Signal()

    def __init__(self, name, label, iconname):
        super().__init__()
        self._name = name
        self._label = label
        self._icon = get_icon(iconname)

        self.setup_page()
        self.load_settings_from_conf()

    def name(self):
        """
        Return the name that will be used to reference this confpage
        in the code.
        """
        return self._name

    def label(self):
        """
        Return the label that will be used to reference this confpage in the
        graphical interface.
        """
        return self._label

    def icon(self):
        """Return configuration page icon"""
        return self._icon

    def is_modified(self):
        return self.get_settings() != self.get_settings_from_conf()

    def apply_changes(self):
        """Apply changes."""
        self.save_settings_to_conf()


class ConfPage(ConfPageBase):
    """
    Sardes configuration page class.

    All configuration page *must* inherit this class and
    reimplement its interface.
    """

    def __init__(self, name, label, iconname):
        """
        Parameters
        ----------
        name: str
            The name that is used to reference this confpage in the code.
        label: str
            The label that is used to reference this confpage in the
            graphical interface.
        icon: str or QIcon
            The name of the icon that appears in the tab for that confpage
            in the tab bar of the configuration dialog
        """
        super().__init__(name, label, iconname)

    def setup_page(self):
        """Setup configuration page widget"""
        raise NotImplementedError

    def get_settings(self):
        """Return the settings that are set in this configuration page."""
        raise NotImplementedError

    def get_settings_from_conf(self):
        """Get settings from the user configuration files."""
        raise NotImplementedError

    def load_settings_from_conf(self):
        """Load settings from the user configuration files."""
        raise NotImplementedError

    def save_settings_to_conf(self):
        """Save settings to the user configuration files."""
        raise NotImplementedError


if __name__ == '__main__':
    app = QApplication(sys.argv)
    sys.exit(app.exec_())
