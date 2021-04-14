# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Standard library imports
import os

# ---- Third party imports
from qtpy.QtCore import Qt
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import QSplashScreen

# ---- Local imports
from sardes import __rootdir__


SPLASH_IMG = os.path.join(__rootdir__, 'ressources', 'sardes_splash.png')


class SplashScreen(QSplashScreen):
    def __init__(self, msg=None):
        super().__init__(QPixmap(SPLASH_IMG))
        if msg is not None:
            self.showMessage(msg)
        self.show()
        self.activateWindow()
        self.raise_()

    def showMessage(self, msg):
        """Override Qt method."""
        super().showMessage(msg, Qt.AlignBottom | Qt.AlignCenter)
