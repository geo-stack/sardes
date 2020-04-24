# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Third party imports
from qtpy.QtCore import Qt, Signal, QSize
from qtpy.QtWidgets import QMainWindow, QToolButton, QFrame, QGridLayout

# ---- Local imports
from sardes.config.icons import get_icon
from sardes.config.locale import _
from sardes.config.gui import get_iconsize
from sardes.utils.qthelpers import (create_mainwindow_toolbar, format_tooltip,
                                    create_toolbutton)


class SardesDockingButton(QFrame):
    """
    This Qt frame contains two stacked toolbuttons that are shown and hidden in
    alternance when clicked on. Two buttons are required to work around a
    know Qt bug where the clicked button remains highlighted when clicked on
    if we only use a single button.

    https://forum.qt.io/topic/103786/qtoolbutton-remains-highlighted-after-press
    """

    sig_undock_pane = Signal()
    sig_dock_pane = Signal()

    def __init__(self, plugin_name, is_docked, parent=None):
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._dock_btn = create_toolbutton(
            self,
            icon='pane_dock',
            text=_("Dock {}".format(plugin_name)),
            tip=_("Dock {} in the main window.".format(plugin_name)),
            triggered=self._handle_dock_triggered,
            iconsize=get_iconsize()
            )
        self._dock_btn.setVisible(not is_docked)
        self._undock_btn = create_toolbutton(
            self,
            icon='pane_undock',
            text=_("Undock {}".format(plugin_name)),
            tip=_("Show {} in a new window.".format(plugin_name)),
            triggered=self._handle_undock_triggered,
            iconsize=get_iconsize()
            )
        self._undock_btn.setVisible(is_docked)
        layout.addWidget(self._dock_btn, 0, 0)
        layout.addWidget(self._undock_btn, 0, 0)

    def set_docked(self, docked):
        """
        Set whether the button should represent a pane that is docked or not.
        """
        self._dock_btn.setVisible(not docked)
        self._undock_btn.setVisible(docked)

    def _handle_dock_triggered(self):
        """
        Handle when the button to dock the pane is clicked.
        """
        self._dock_btn.hide()
        self.sig_dock_pane.emit()
        self._undock_btn.show()

    def _handle_undock_triggered(self):
        """
        Handle when the button to undock the pane is clicked.
        """
        self._undock_btn.hide()
        self.sig_undock_pane.emit()
        self._dock_btn.show()


class SardesPaneWidget(QMainWindow):
    """
    Sardes pane widget class.

    All plugin that need to add a pane to Sardes mainwindow *must* use this
    class to encapsulate their main interface.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._upper_toolbar = None
        self._lower_toolbar = None

    # ---- Setup
    def _setup_upper_toolbar(self):
        self._upper_toolbar = create_mainwindow_toolbar("panes_upper_toolbar")
        self._upper_toolbar.setStyleSheet("QToolBar {border: 0px;}")
        self.addToolBar(self._upper_toolbar)

    def _setup_lower_toolbar(self):
        self._lower_toolbar = create_mainwindow_toolbar(
            "panes_lower_toolbar", areas=Qt.BottomToolBarArea)
        self._lower_toolbar.setStyleSheet("QToolBar {border: 0px;}")
        self.addToolBar(self._lower_toolbar)

    # ---- Public methods
    def get_central_widget(self):
        return self.centralWidget()

    def set_central_widget(self, widget):
        self.setCentralWidget(widget)

    def get_upper_toolbar(self):
        if self._upper_toolbar is None:
            self._setup_upper_toolbar()
        return self._upper_toolbar

    def get_lower_toolbar(self):
        if self._lower_toolbar is None:
            self._setup_lower_toolbar()
        return self._lower_toolbar

    def set_iconsize(self, iconsize):
        """Set the icon size of this pane toolbars."""
        pass

    def register_to_plugin(self, plugin):
        """Register the current widget to the given plugin."""
        pass
