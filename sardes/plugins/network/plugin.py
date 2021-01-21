# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

import os.path as osp

# ---- Third party imports
import simplekml

# ---- Local imports
from sardes.api.plugins import SardesPlugin
from sardes.config.database import get_dbconfig, set_dbconfig
from sardes.config.locale import _
from sardes.utils.qthelpers import (create_mainwindow_toolbar,
                                    create_toolbutton)
from sardes.plugins.network.widgets import PublishNetworkDialog


"""Piezometric Network plugin"""


class PiezometricNetwork(SardesPlugin):

    CONF_SECTION = 'piezometric_network'

    def __init__(self, parent):
        super().__init__(parent)

    @classmethod
    def get_plugin_title(cls):
        """Return widget title"""
        return _('Piezometric Network')

