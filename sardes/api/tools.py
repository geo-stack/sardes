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
from qtpy.QtCore import QObject, Qt, Slot, QPoint, Signal, QEvent, QSize
from qtpy.QtWidgets import (QApplication, QToolButton, QLabel, QToolBar,
                            QMainWindow, QAction)

# ---- Local imports
from sardes.config.icons import get_icon
from sardes.config.gui import get_iconsize
from sardes.utils.qthelpers import create_toolbutton, format_tooltip


class SardesToolBase(QAction):
    """
    Basic functionality for Sardes tools.

    WARNING: Don't override any methods or attributes present here unless you
    know what you are doing.
    """

    def __init__(self, parent, name, text, icon, tip=None, iconsize=None,
                 shortcut=None, context=Qt.WindowShortcut):
        """
        Parameters
        ----------
        parent : object
            The parent Qt object where this tool is installed.
        name : str
            The name that will be used to reference this tool in the code.
        text: str
            The str that will be used for the tooltip title and
            toolwidget window title.
        tip: str
            The str that will be used for the tooltip description.
        icon: str or QIcon
            A QIcon object or a string to fetch from the configs the icon that
            will be used for the toolbutton and the toolwidget's window.
        shortcut: str
            A string corresponding to the keyboard shortcut to use for
            triggering this tool.
        """
        super().__init__(text, parent)
        self.setObjectName(name)
        self._text = text
        self.setToolTip(format_tooltip(text, tip, shortcut))

        self.setIcon(get_icon(icon) if isinstance(icon, str) else icon)
        iconsize = iconsize or get_iconsize()

        self.triggered.connect(self.__triggered__)
        if shortcut is not None:
            if isinstance(shortcut, (list, tuple)):
                self.setShortcuts(shortcut)
            else:
                self.setShortcut(shortcut)
            self.setShortcutContext(context)

        self._toolbutton = None
        self._toolwidget = None

        self.parent = parent
        parent.installEventFilter(self)

    # ---- Public API
    def update(self):
        """Update the tool and its associated toolwidget if any."""
        self.__update__()

    def toolwidget(self):
        """Return the main widget of this tool."""
        if self._toolwidget is None:
            # We only create the toolwidget when it is needed to reduce
            # the startup time and footprint of the application.
            self._toolwidget = self.__create_toolwidget__()
            self.update()
        return self._toolwidget

    def toolbutton(self):
        """Return a Qt toolbutton that trigger this tool when clicked."""
        if self._toolbutton is None:
            self._toolbutton = QToolButton()
            self._toolbutton.setDefaultAction(self)
            iconsize = get_iconsize()
            self._toolbutton.setIconSize(QSize(iconsize, iconsize))
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
        if self.toolwidget() is not None:
            self._show_toolwidget()

    # ---- Private API
    def eventFilter(self, widget, event):
        """
        An event filter to close this tool when it's parent is closed.
        """
        if event.type() == QEvent.Close:
            self.close()
        return super().eventFilter(widget, event)

    def _show_toolwidget(self):
        """Show this tool's main widget."""
        if self._toolwidget.windowState() == Qt.WindowMinimized:
            self._toolwidget.setWindowState(Qt.WindowNoState)
        if self._toolwidget.windowType() == Qt.Widget:
            self._toolwidget.setWindowFlags(
                self._toolwidget.windowFlags() | Qt.Window)
        self._toolwidget.setWindowIcon(self.icon())
        self._toolwidget.setWindowTitle(self.__title__())
        self._toolwidget.show()
        self._toolwidget.activateWindow()
        self._toolwidget.raise_()


class SardesTool(SardesToolBase):
    """
    Sardes abstract tool class.

    A Sardes tool is a QAction that can be used to perform an action directly
    when triggered or to show a widget window to do more complex operations.
    """

    def __create_toolwidget__(self):
        """
        Create and return the main widget that will be shown when this tool
        is triggered.

        All tools that need to show a dialog window when triggered *must*
        reimplement this method and return a valid QWidget object.
        """
        return None

    def __triggered__(self):
        """
        This is the function that is called when this tool is triggered.

        By default, the widget returned by __create_toolwidget__ is shown. This
        method can be reimplemented to perform other any other actions.
        """
        self.show()

    def __title__(self):
        """
        Return the title that is used for the toolwidget's window.

        By default, the tool's text is used. All tools that need to set a
        different title for their toolwidget window need to reimplement this
        method.
        """
        return self._text

    def __update__(self):
        """Update the tool and its associated toolwidget if any."""
        raise NotImplementedError


class SardesToolExample(SardesTool):
    """
    Sardes tool concrete implementation example.
    """

    def __init__(self, parent):
        super().__init__(
            parent,
            name='sardes_tool_example',
            text='Sardes Tool Example',
            icon='information',
            tip=('This is an example that show an implementation of '
                 'a Sardes tool.'),
            shortcut='Ctrl+E'
            )

    def __create_toolwidget__(self):
        widget = QLabel('This is a Sardes tool example.')
        widget.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        widget.setFixedSize(300, 150)
        return widget


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)

    toolbar = QToolBar()

    mainwindow = QMainWindow()
    mainwindow.addToolBar(toolbar)

    tool = SardesToolExample(parent=mainwindow)
    toolbar.addAction(tool)

    mainwindow.show()

    sys.exit(app.exec_())
