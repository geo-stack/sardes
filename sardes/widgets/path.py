# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard library imports
import os.path as osp

# ---- Third party imports
from appconfigs.base import get_home_dir
from qtpy.QtWidgets import (
    QCheckBox, QFrame, QLineEdit, QLabel, QFileDialog, QPushButton,
    QGridLayout)

# ---- Local imports
from sardes.config.locale import _


class PathBoxWidget(QFrame):
    """
    A widget to display and select a directory or file location.
    """

    def __init__(self, parent=None, path='', workdir='',
                 path_type='getExistingDirectory', filters=None):
        super().__init__(parent)
        self._workdir = workdir
        self.filters = filters
        self._path_type = path_type

        self.browse_btn = QPushButton(_("Browse..."))
        self.browse_btn.setDefault(False)
        self.browse_btn.setAutoDefault(False)
        self.browse_btn.clicked.connect(self.browse_path)

        self.path_lineedit = QLineEdit()
        self.path_lineedit.setReadOnly(True)
        self.path_lineedit.setText(path)
        self.path_lineedit.setToolTip(path)
        self.path_lineedit.setFixedHeight(
            self.browse_btn.sizeHint().height() - 2)

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        layout.addWidget(self.path_lineedit, 0, 0)
        layout.addWidget(self.browse_btn, 0, 1)

    def is_valid(self):
        """Return whether path is valid."""
        return osp.exists(self.path())

    def is_empty(self):
        """Return whether the path is empty."""
        return self.path_lineedit.text() == ''

    def path(self):
        """Return the path of this pathbox widget."""
        return self.path_lineedit.text()

    def set_path(self, path):
        """Set the path to the specified value."""
        return self.path_lineedit.setText(path)

    def browse_path(self):
        """Open a dialog to select a new directory."""
        dialog_title = _('Modify Location')
        if self._path_type == 'getExistingDirectory':
            path = QFileDialog.getExistingDirectory(
                self, dialog_title, self.workdir(),
                options=QFileDialog.ShowDirsOnly)
        elif self._path_type == 'getOpenFileName':
            path, ext = QFileDialog.getOpenFileName(
                self, dialog_title, self.workdir(), self.filters)
        elif self._path_type == 'getSaveFileName':
            path, ext = QFileDialog.getSaveFileName(
                self, dialog_title, self.workdir())
        if path:
            self.set_workdir(osp.dirname(path))
            self.path_lineedit.setText(path)
            self.path_lineedit.setToolTip(path)

    def workdir(self):
        """Return the directory that is used by the QFileDialog."""
        return self._workdir if osp.exists(self._workdir) else get_home_dir()

    def set_workdir(self, new_workdir):
        """Set the default directory that will be used by the QFileDialog."""
        if new_workdir is not None and osp.exists(new_workdir):
            self._workdir = new_workdir


class CheckboxPathBoxWidget(QFrame):
    """
    A widget to display and select a directory or file location, with
    a checkbox to enable or disable the widget and a group label.
    """

    def __init__(self, parent=None, label='', path='',
                 is_enabled=True, workdir=''):
        super().__init__(parent)
        self.label = label

        self.pathbox_widget = PathBoxWidget(parent=self, workdir=workdir)

        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(
            lambda _: self.pathbox_widget.setEnabled(self.is_enabled()))
        self.checkbox.setChecked(is_enabled)

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.checkbox, 0, 0)
        layout.addWidget(QLabel(label + ' :' if label else label), 0, 1)
        layout.addWidget(self.pathbox_widget, 1, 1)

    def is_enabled(self):
        """Return whether this pathbox widget is enabled or not."""
        return self.checkbox.isChecked()

    def set_enabled(self, enabled):
        self.checkbox.setChecked(enabled)

    # ---- PathBoxWidget public API
    def is_valid(self):
        return self.pathbox_widget.is_valid()

    def is_empty(self):
        return self.pathbox_widget.is_empty()

    def path(self):
        return self.pathbox_widget.path()

    def set_path(self, path):
        return self.pathbox_widget.set_path(path)

    def browse_path(self):
        return self.pathbox_widget.browse_path()

    def workdir(self):
        return self.pathbox_widget.workdir()

    def set_workdir(self, new_workdir):
        return self.pathbox_widget.set_workdir(new_workdir)
