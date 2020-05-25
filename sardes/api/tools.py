# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports
import os

# ---- Third party imports
from qtpy.QtCore import QObject, Qt, Slot, QPoint, Signal, QEvent

# ---- Local imports
from sardes.config.icons import get_icon
from sardes.config.gui import get_iconsize
from sardes.utils.qthelpers import create_toolbutton


class SardesToolBase(QObject):
    """
    Basic functionality for Sardes tools.

    WARNING: Don't override any methods or attributes present here unless you
    know what you are doing.
    """

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self._toolwidget = None
        self._toolbutton = None
        self._hidden_with_parent = False
        parent.installEventFilter(self)

    # ---- Public API
    def toolbutton(self):
        """
        Return the toolbutton that is used to show this tools' widget
        when clicked on.
        """
        if self._toolbutton is None:
            self._toolbutton = self._create_toolbutton()
        return self._toolbutton

    def close(self):
        """Close this tool."""
        if self._toolwidget is not None:
            self._toolwidget.close()

    def hide(self):
        """Hide this tool."""
        if self._toolwidget is not None:
            self._toolwidget.hide()

    def show(self):
        """Show this tool."""
        if self._toolwidget is not None:
            self._toolwidget.show()

    # ---- Private API
    def eventFilter(self, widget, event):
        """
        An event filter to close this tool when it's parent is closed.
        """
        if event.type() == QEvent.Close:
            self.close()
        elif event.type() == QEvent.Hide:
            self._hidden_with_parent = (
                self._toolwidget is not None and
                self._toolwidget.isVisible())
            self.hide()
        elif event.type() == QEvent.Show:
            if self._hidden_with_parent is True:
                self.show()
        return super().eventFilter(widget, event)

    def _create_toolbutton(self):
        """
        Create and return the toolbutton that is used to show this
        tools' widget when clicked on.
        """
        return create_toolbutton(
            None, icon=self.icon(), text=self.text(), tip=self.tip(),
            triggered=self._show_toolwidget,
            iconsize=get_iconsize()
            )

    def _setup_toolwidget(self):
        """Setup this tool's main widget."""
        self._toolwidget = self.toolwidget()
        self._toolwidget.setWindowIcon(get_icon(self.icon()))
        self._toolwidget.setWindowTitle(self.title())
        self._toolwidget.setWindowFlags(
            self._toolwidget.windowFlags() | Qt.Window)

    @Slot(bool)
    def _show_toolwidget(self, checked):
        """Show this tool's main widget."""
        if self._toolwidget is None:
            self._setup_toolwidget()
        if self._toolwidget.windowState() == Qt.WindowMinimized:
            self._toolwidget.setWindowState(Qt.WindowNoState)
        self._toolwidget.show()
        self._toolwidget.activateWindow()
        self._toolwidget.raise_()


class SardesTool(SardesToolBase):
    """
    Sardes abstract tool class.

    A Sardes tool consists mainly of a toolbutton and a widget that
    is shown when that toolbutton is clicked.
    """

    def toolwidget(self):
        """Return the main widget of this tool."""
        raise NotImplementedError

    def icon(self):
        """
        Return the icon that will be used for the toolbutton and
        toolwidget's window.
        """
        raise NotImplementedError

    def text(self):
        """Return the text that will be used for the toolbutton."""
        raise NotImplementedError

    def tip(self):
        """Return the tooltip text that will be used for the toolbutton."""
        raise NotImplementedError

    def title(self):
        """Return the title that will be used for the toolwidget's window."""
        raise NotImplementedError


