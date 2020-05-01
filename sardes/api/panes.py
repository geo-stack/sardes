# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports
import uuid

# ---- Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMainWindow

# ---- Local imports
from sardes.utils.qthelpers import create_mainwindow_toolbar


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
        self.setObjectName(str(uuid.uuid4()))
        self.setStyleSheet("QMainWindow#%s {border: 0px;}" % self.objectName())
        self.setContextMenuPolicy(Qt.NoContextMenu)

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
