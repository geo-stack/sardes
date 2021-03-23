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
import os.path as osp

# ---- Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QApplication, QLabel, QMessageBox, QPushButton, QFileDialog)

# ---- Local imports
from sardes.api.database_dialog import DatabaseConnectDialogBase
from sardes.config.locale import _
from sardes.config.ospath import (
    get_select_file_dialog_dir, set_select_file_dialog_dir)
from sardes.database.accessors import DatabaseAccessorSardesLite
from sardes.utils.qthelpers import format_tooltip
from sardes.widgets.path import PathBoxWidget


class DatabaseConnectDialogSardesLite(DatabaseConnectDialogBase):
    """
    Sardes database dialog class.

    This is the concrete class that provides a gui for the Sardes SQLite
    database accessor.
    """
    # The concrete database accessor class this dialog
    # is providing an interface to.
    __DatabaseAccessor__ = DatabaseAccessorSardesLite
    __database_type_name__ = 'Sardes SQLite'

    FILEFILTER = 'Sardes SQLite Database (*.db)'

    def __init__(self):
        super().__init__()

        self.dbname_widget = PathBoxWidget(
            path_type='getOpenFileName', filters=self.FILEFILTER)
        self.dbname_widget.browse_btn.setToolTip(format_tooltip(
            text=_("Select Database"),
            tip=_("Select an existing Sardes SQLite database."),
            shortcuts=None
            ))
        self.dbname_widget.path_lineedit.setMinimumWidth(200)

        self.create_btn = QPushButton(_("Create..."))
        self.create_btn.setDefault(False)
        self.create_btn.setAutoDefault(False)
        self.create_btn.setToolTip(format_tooltip(
            text=_("Create Database"),
            tip=_("Create a new Sardes SQLite database."),
            shortcuts=None
            ))
        self.create_btn.clicked.connect(lambda _: self.select_new_database())
        self.dbname_widget.layout().addWidget(self.create_btn, 0, 2)

        self.form_layout.setRowMinimumHeight(0, 15)
        self.add_widget(QLabel(_("Database :")), 1, 0)
        self.add_widget(self.dbname_widget, 1, 1)
        self.add_stretch(1)

    @property
    def browse_btn(self):
        return self.dbname_widget.browse_btn

    def set_database_kargs(self, kargs):
        if 'database' in kargs:
            self.dbname_widget.set_path(kargs['database'])
            self.dbname_widget.path_lineedit.setToolTip(
                kargs['database'])

    def get_database_kargs(self):
        """
        Return a dict that must match the constructor kargs signature of the
        database accessor class for which this dialog is providing an
        an interface to.
        """
        return {'database': self.dbname_widget.path()}

    # ---- Manage database creation
    def select_new_database(self, filename=None):
        """
        Open a file dialog to allow the user to select a filename
        that will be used to create a new Sardes database.

        Parameters
        ----------
        filename : str
            The absolute path of the default database file that will be set in
            the file dialog.
        """
        if filename is None:
            dirname = get_select_file_dialog_dir()
            filename = osp.join(dirname, 'SardesDatabase1.db')
            i = 1
            while osp.exists(filename):
                i += 1
                filename = osp.join(dirname, 'SardesDatabase{}.db'.format(i))

        filename, filefilter = QFileDialog.getSaveFileName(
            self, _('New Database'), filename, self.FILEFILTER)
        if filename:
            filename = osp.abspath(filename)
            set_select_file_dialog_dir(osp.dirname(filename))
            if not filename.endswith('.db'):
                filename += '.db'
            self.create_database(filename)

    def create_database(self, filename):
        """
        Create a new database using the provided database filename.

        Parameters
        ----------
        filename : str
            The absolute filepath where we want to create the database.
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()
        if osp.exists(filename):
            try:
                os.remove(filename)
            except PermissionError:
                QApplication.restoreOverrideCursor()
                QApplication.processEvents()
                QMessageBox.warning(
                    self.main,
                    _('New Database Error'),
                    _("Cannot overwrite Sardes database at <i>{}</i>  "
                      "because it is already in use by another "
                      "application or user.").format(filename),
                    QMessageBox.Ok)
                self.select_new_database(filename)
                return

        print("Creating database {}...".format(filename))
        accessor = DatabaseAccessorSardesLite(filename)
        accessor.init_database()
        accessor.close_connection()
        self.set_database_kargs({'database': filename})
        print("Database {} created successfully.".format(filename))
        QApplication.restoreOverrideCursor()
        QApplication.processEvents()
