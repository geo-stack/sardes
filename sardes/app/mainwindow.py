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
from qtpy.QtCore import QSize, Qt
from qtpy.QtWidgets import QApplication, QLabel, QMainWindow

# ---- Local imports
from sardes.config.icons import get_icon
from sardes.config.gui import get_iconsize

from multiprocessing import freeze_support
freeze_support()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Toolbars
        self.visible_toolbars = []
        self.toolbarslist = []

        label = QLabel('Welcome to Sardes!')
        label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(label)

    # ---- Window setup
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
