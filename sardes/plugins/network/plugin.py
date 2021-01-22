# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

import os.path as osp

# ---- Local imports
from sardes.api.plugins import SardesPlugin
from sardes.config.database import get_dbconfig, set_dbconfig
from sardes.config.locale import _
from sardes.utils.qthelpers import (
    create_mainwindow_toolbar, create_toolbutton)
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

    def setup_plugin(self):
        """Setup this plugin."""
        self.publish_dialog = PublishNetworkDialog(
            self.main,
            is_iri_data=self.get_option('publish/is_iri_data', False),
            iri_data=self.get_option('publish/iri_data', ''),
            is_iri_logs=self.get_option('publish/is_iri_logs', False),
            iri_logs=self.get_option('publish/iri_logs', ''),
            is_iri_graphs=self.get_option('publish/is_iri_graphs', False),
            iri_graphs=self.get_option('publish/iri_graphs', '')
            )
        self.publish_dialog.sig_start_publish_network_request.connect(
            self._start_publishing_network)

    def create_mainwindow_toolbars(self):
        toolbar = create_mainwindow_toolbar("Publish toolbar")

        # Setup the database connection button.
        self.show_publish_dialog_btn = create_toolbutton(
            self.main,
            triggered=self.publish_dialog.show,
            text=_("Publish"),
            tip=_("Open a dialog window to publish the data "
                  "of the piezometric network."),
            icon='publish_piezometric_network'
            )
        toolbar.addWidget(self.show_publish_dialog_btn)

        return [toolbar]

    def close_plugin(self):
        """
        Extend Sardes plugin method to save user inputs in the
        configuration file.
        """
        super().close_plugin()
        self.set_option(
            'publish/is_iri_data', self.publish_dialog.is_iri_data())
        self.set_option(
            'publish/iri_data', self.publish_dialog.iri_data())
        self.set_option(
            'publish/is_iri_logs', self.publish_dialog.is_iri_logs())
        self.set_option(
            'publish/iri_logs', self.publish_dialog.iri_logs())
        self.set_option(
            'publish/is_iri_graphs', self.publish_dialog.is_iri_graphs())
        self.set_option(
            'publish/iri_graphs', self.publish_dialog.iri_graphs())

    # ---- Publish Network
    def _show_publishing_tool():
        pass

    def _start_publishing_network(self, filename):
        self.main.db_connection_manager.publish_to_kml(
            filename=filename,
            iri_data=self.publish_dialog.iri_data(),
            callback=self._stop_publishing_network
            )

    def _stop_publishing_network(self):
        self.publish_dialog.stop_publishing()
