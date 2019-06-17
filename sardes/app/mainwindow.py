# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports
import sys

# ---- Third party imports
from qtpy.QtCore import QSize, Qt, QUrl
from qtpy.QtGui import QDesktopServices
from qtpy.QtWidgets import (QApplication, QLabel, QMainWindow, QMenu,
                            QSizePolicy, QToolButton, QWidget)

# ---- Local imports
from sardes import __project_url__
from sardes.config.icons import get_icon
from sardes.config.gui import get_iconsize
from sardes.database.connection import BDConnManager
from sardes.utils.qthelpers import create_action, create_toolbutton

from multiprocessing import freeze_support
freeze_support()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Toolbars
        self.visible_toolbars = []
        self.toolbarslist = []


        self.setup()

    def setup(self):
        """Setup the main window"""
        label = QLabel('Welcome to Sardes!')
        label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(label)

        self.create_topright_corner_toolbar()

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

    def create_toolbar(self, title, object_name, iconsize=None):
        """Create and return a toolbar with title and object_name."""
        toolbar = self.addToolBar(title)
        toolbar.setObjectName(object_name)
        iconsize = get_iconsize() if iconsize is None else iconsize
        toolbar.setIconSize(QSize(iconsize, iconsize))
        self.toolbarslist.append(toolbar)
        return toolbar


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())
