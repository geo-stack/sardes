# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Standard imports
import datetime
import os.path as osp
import sys

# ---- Third party imports
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QApplication, QAbstractButton, QCheckBox, QComboBox, QDialog,
    QDialogButtonBox, QHBoxLayout, QLabel, QPushButton, QStackedWidget,
    QVBoxLayout, QGridLayout, QLineEdit, QFileDialog, QGroupBox,
    QMessageBox)

# ---- Local imports
from sardes.config.icons import get_icon
from sardes.config.locale import _
from sardes.config.ospath import (
    get_select_file_dialog_dir, set_select_file_dialog_dir)
from sardes.widgets.statusbar import ProcessStatusBar


class PublishNetworkDialog(QDialog):
    """
    A dialog window to manage the connection to the database.
    """
    sig_closed = Signal()
    sig_start_publish_network_request = Signal(str)
    sig_cancel_publish_network_request = Signal()

    def __init__(self, parent=None, is_iri_data=False, iri_data='',
                 is_iri_logs=False, iri_logs='', is_iri_graphs=False,
                 iri_graphs=''):
        super().__init__(parent)
        self.setWindowTitle(_('Publish Piezometric Network Data'))
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setWindowIcon(get_icon('publish_piezometric_network'))
        self.setModal(False)
        self.setWindowModality(Qt.ApplicationModal)

        self._publishing_in_progress = False
        self._setup(is_iri_data, iri_data, is_iri_logs, iri_logs,
                    is_iri_graphs, iri_graphs)

    def _setup(self, is_iri_data, iri_data, is_iri_logs, iri_logs,
               is_iri_graphs, iri_graphs):
        """
        Setup the dialog with the provided settings.
        """
        # Setup database type selection combobox.
        self.iri_data_ledit = QLineEdit()
        self.iri_data_ledit.setText(iri_data)
        self.iri_data_ledit.setEnabled(is_iri_data)

        self.iri_logs_ledit = QLineEdit()
        self.iri_logs_ledit.setText(iri_logs)
        self.iri_logs_ledit.setEnabled(is_iri_logs)

        self.iri_graphs_ledit = QLineEdit()
        self.iri_graphs_ledit.setText(iri_graphs)
        self.iri_graphs_ledit.setEnabled(is_iri_graphs)

        self.iri_data_chbox = QCheckBox()
        self.iri_data_chbox.setChecked(is_iri_data)
        self.iri_data_chbox.stateChanged.connect(
            lambda _: self.iri_data_ledit.setEnabled(
                self.iri_data_chbox.isChecked()))

        self.iri_logs_chbox = QCheckBox()
        self.iri_logs_chbox.setChecked(is_iri_logs)
        self.iri_logs_chbox.stateChanged.connect(
            lambda _: self.iri_logs_ledit.setEnabled(
                self.iri_logs_chbox.isChecked()))

        self.iri_graphs_chbox = QCheckBox()
        self.iri_graphs_chbox.setChecked(is_iri_graphs)
        self.iri_graphs_chbox.stateChanged.connect(
            lambda _: self.iri_graphs_ledit.setEnabled(
                self.iri_graphs_chbox.isChecked()))

        self.iri_groupbox = QGroupBox(_('Attached Files'))
        iri_layout = QGridLayout(self.iri_groupbox)
        iri_layout.addWidget(self.iri_data_chbox, 0, 0)
        iri_layout.addWidget(self.iri_logs_chbox, 1, 0)
        iri_layout.addWidget(self.iri_graphs_chbox, 2, 0)

        iri_layout.addWidget(QLabel(_("Readings Data")), 0, 1)
        iri_layout.addWidget(QLabel(_("Construction Logs")), 1, 1)
        iri_layout.addWidget(QLabel(_("Hydrographs")), 2, 1)

        iri_layout.setColumnMinimumWidth(2, 25)

        iri_layout.addWidget(QLabel(_("IRI:")), 0, 3)
        iri_layout.addWidget(QLabel(_("IRI:")), 1, 3)
        iri_layout.addWidget(QLabel(_("IRI:")), 2, 3)

        iri_layout.addWidget(self.iri_data_ledit, 0, 4)
        iri_layout.addWidget(self.iri_logs_ledit, 1, 4)
        iri_layout.addWidget(self.iri_graphs_ledit, 2, 4)
        iri_layout.setColumnMinimumWidth(4, 400)

        # Setup the status bar.
        self.status_bar = ProcessStatusBar()
        self.status_bar.hide()

        # Setup the dialog button box.
        self.publish_button = QPushButton(_('Publish'))
        self.publish_button.setDefault(True)
        self.publish_button.clicked.connect(self._select_kml_save_file)

        self.close_button = QPushButton(_('Close'))
        self.close_button.setDefault(False)
        self.close_button.setAutoDefault(False)
        self.close_button.clicked.connect(self.close)

        button_box = QDialogButtonBox()
        button_box.addButton(self.publish_button, button_box.ApplyRole)
        button_box.addButton(self.close_button, button_box.RejectRole)
        button_box.layout().insertSpacing(1, 100)

        # Setup the main layout.
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.iri_groupbox)
        main_layout.addSpacing(15)
        main_layout.addWidget(self.status_bar)
        main_layout.addWidget(button_box)
        main_layout.setStretch(0, 1)
        main_layout.setSizeConstraint(main_layout.SetFixedSize)

    def is_iri_data(self):
        return self.iri_data_chbox.isChecked()

    def iri_data(self):
        return self.iri_data_ledit.text()

    def is_iri_logs(self):
        return self.iri_logs_chbox.isChecked()

    def iri_logs(self):
        return self.iri_logs_ledit.text()

    def is_iri_graphs(self):
        return self.iri_graphs_chbox.isChecked()

    def iri_graphs(self):
        return self.iri_graphs_ledit.text()

    # ---- Handlers
    def _select_kml_save_file(self):
        dirname = get_select_file_dialog_dir()
        filename = _('Piezometric_Network_{}.kml').format(
            datetime.datetime.now().strftime('%Y-%m-%d'))
        filefilters = 'Keyhole Markup Language (*.kml)'
        filename, filefilter = QFileDialog.getSaveFileName(
            self, _('Publish As'), osp.join(dirname, filename), filefilters)
        if filename:
            filename = osp.abspath(filename)
            if not filename.endswith('.kml'):
                filename += '.kml'
            set_select_file_dialog_dir(osp.dirname(filename))

            self.start_publishing(filename)

    def start_publishing(self, filename):
        self._publishing_in_progress = True
        self.publish_button.setEnabled(False)
        self.iri_groupbox.setEnabled(False)
        self.status_bar.show(_("Publishing piezometric network data..."))
        self.sig_start_publish_network_request.emit(filename)

    def stop_publishing(self, result):
        self._publishing_in_progress = False
        self.publish_button.setEnabled(True)
        self.iri_groupbox.setEnabled(True)
        if result is True:
            self.status_bar.show_sucess_icon(
                message=_("Piezometric network data published successfully."))
        else:
            self.status_bar.show_fail_icon(
                message=_("Failed to publish piezometric network data."))

    def closeEvent(self, event):
        """Override Qt method to emit a signal when closing."""
        if self._publishing_in_progress:
            answer = QMessageBox.question(
                self, _("Cancel Publishing"),
                _("This action will cancel the publishing process.<br><br>"
                  "Do you want to continue?"),
                QMessageBox.Yes | QMessageBox.No)
            if answer == QMessageBox.Yes:
                self.sig_cancel_publish_network_request.emit()

                event.accept()
                self.sig_closed.emit()
                super().closeEvent(event)
            else:
                event.ignore()
        else:
            self.sig_closed.emit()
            super().closeEvent(event)


if __name__ == '__main__':
    pass
