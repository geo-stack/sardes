# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports
import platform
import sys

# ---- Third party imports
from qtpy.QtCore import QEvent, QPoint, QSize, Qt, QUrl
from qtpy.QtGui import QDesktopServices
from qtpy.QtWidgets import (QApplication, QLabel, QMainWindow, QMenu,
                            QSizePolicy, QToolButton, QWidget)

# ---- Local imports
from sardes import __namever__, __project_url__
from sardes.config.icons import get_icon
from sardes.config.gui import (get_iconsize, get_window_settings,
                               set_window_settings)
from sardes.widgets.databaseconnector import DatabaseConnectionWidget
from sardes.utils.qthelpers import create_action, create_toolbutton

from multiprocessing import freeze_support
freeze_support()

GITHUB_ISSUES_URL = __project_url__ + "/issues"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._window_normal_size = [self.size()] * 2
        self._window_normal_pos = [self.pos()] * 2

        self.setWindowIcon(get_icon('master'))
        self.setWindowTitle(__namever__)
        if platform.system() == 'Windows':
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                __namever__)

        # Toolbars
        self.visible_toolbars = []
        self.toolbarslist = []

        self.db_conn_manager = DatabaseConnectionWidget(self)
        self.db_conn_manager.hide()

        self.setup()

    def setup(self):
        """Setup the main window"""
        label = QLabel('Welcome to Sardes!')
        label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(label)

        self.create_topright_corner_toolbar()

        self.set_window_settings(*get_window_settings())

    # ---- Toolbar setup
    def create_topright_corner_toolbar(self):
        """
        Create and add a toolbar to the top right corner of this
        application.
        """
        self.topright_corner_toolbar = self.create_toolbar(
            "Options toolbar", "option_toolbar")
        self.topright_corner_toolbar.setMovable(False)

        # Add a spacer item.
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.topright_corner_toolbar.addWidget(spacer)

        # Add the database connection manager button.
        self.database_button = create_toolbutton(
            self, triggered=self.db_conn_manager.show,
            text="Database connection manager",
            tip="Open the database connection manager window.",
            shortcut='Ctrl+Shift+D')
        self.setup_database_button_icon()
        self.db_conn_manager.sig_connection_changed.connect(
            self.setup_database_button_icon)
        self.topright_corner_toolbar.addWidget(self.database_button)

        # Add the tools and options button.
        self.options_button = self.create_options_button()
        self.topright_corner_toolbar.addWidget(self.options_button)

    def create_options_button(self):
        """Create and return the options button of this application."""
        options_button = create_toolbutton(
            self, icon='tooloptions',
            text="Tools and options",
            tip="Open the tools and options menu.",
            shortcut='Ctrl+Shift+T')
        options_button.setStyleSheet(
            "QToolButton::menu-indicator{image: none;}")
        options_button.setPopupMode(QToolButton.InstantPopup)

        # Create the tools and options menu.
        options_menu = self.create_options_menu()
        options_button.setMenu(options_menu)

        return options_button

    def create_options_menu(self):
        """Create and return the options menu of this application."""
        options_menu = QMenu(self)

        report_action = create_action(
            self, 'Report issue...', icon='bug',
            shortcut='Ctrl+Shift+R', context=Qt.ApplicationShortcut,
            triggered=lambda: QDesktopServices.openUrl(QUrl(GITHUB_ISSUES_URL))
            )
        about_action = create_action(
            self, 'About Sardes...', icon='information',
            shortcut='Ctrl+Shift+I', context=Qt.ApplicationShortcut
            )
        exit_action = create_action(
            self, 'Exit', icon='exit', triggered=self.close,
            shortcut='Ctrl+Shift+Q', context=Qt.ApplicationShortcut
            )

        for action in [report_action, about_action, exit_action]:
            options_menu.addAction(action)

        return options_menu

    def create_toolbar(self, title, object_name, iconsize=None):
        """Create and return a toolbar with title and object_name."""
        toolbar = self.addToolBar(title)
        toolbar.setObjectName(object_name)
        iconsize = get_iconsize() if iconsize is None else iconsize
        toolbar.setIconSize(QSize(iconsize, iconsize))
        self.toolbarslist.append(toolbar)
        return toolbar

    def setup_database_button_icon(self):
        """
        Set the icon of the database button to show whether a database is
        currently connected or not.
        """
        db_icon = ('database_connected' if self.db_conn_manager.is_connected()
                   else 'database_disconnected')
        self.database_button.setIcon(get_icon(db_icon))

    # ---- Main window settings
    def get_window_settings(self):
        """Return current window settings."""
        window_size = (self._window_normal_size[1].width(),
                       self._window_normal_size[1].height())
        window_position = (self._window_normal_pos[1].x(),
                           self._window_normal_pos[1].y())
        is_maximized = self.isMaximized()
        return (window_size, window_position, is_maximized)

    def set_window_settings(self, window_size, window_position, is_maximized):
        """Set window settings"""
        self._window_normal_size = [QSize(*window_size)] * 2
        self._window_normal_pos = [QPoint(*window_position)] * 2

        self.resize(*window_size)
        self.move(*window_position)

        self.setWindowState(Qt.WindowNoState)
        if is_maximized:
            self.setWindowState(self.windowState() ^ Qt.WindowMaximized)
        self.setAttribute(Qt.WA_Resized, True)
        # Setting the Qt.WA_Resized attribute to True is required or else the
        # size of the wigdet will not be updated correctly when restoring the
        # window from a maximized state and the layout won't be expanded
        # correctly to the full size of the widget.

    # ---- Main window events
    def closeEvent(self, event):
        """Reimplement Qt closeEvent."""
        set_window_settings(*self.get_window_settings())
        event.accept()

    def changeEvent(self, event):
        """Reimplement Qt method."""
        # We need to restore the values for the normal window size and
        # position that were stored in the resizeEvent() and moveEvent()
        # to their previous value because isMaximized() does not work as
        # expected when when within the resizeEvent() and moveEvent()
        # caused by the window maximization. It seems as if the state returned
        # by isMaximized() is set AFTER the resizeEvent() and moveEvent()
        # were executed.
        #
        # See this bug https://bugreports.qt.io/browse/QTBUG-30085 for
        # more information.
        if event.type() == QEvent.WindowStateChange:
            if self.windowState() & Qt.WindowMaximized:
                self._window_normal_size[1] = self._window_normal_size[0]
                self._window_normal_pos[1] = self._window_normal_pos[0]
        super().changeEvent(event)

    def resizeEvent(self, event):
        """Reimplement Qt method."""
        if not self.isMaximized():
            self._window_normal_size[0] = self._window_normal_size[1]
            self._window_normal_size[1] = self.size()
        super().resizeEvent(event)

    def moveEvent(self, event):
        """Reimplement Qt method."""
        if not self.isMaximized():
            self._window_normal_pos[0] = self._window_normal_pos[1]
            self._window_normal_pos[1] = self.pos()
        super().moveEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())
