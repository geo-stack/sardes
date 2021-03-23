# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Stantard imports
import os
import os.path as osp
from shutil import rmtree

# ---- Third party imports
from appconfigs.base import get_home_dir
from qtpy.QtCore import Qt, QObject
from qtpy.QtWidgets import QApplication, QFileDialog, QMessageBox

# ---- Local imports
from sardes.config.locale import _


def delete_file_safely(filename):
    """Try to delete a file on the disk and return the error if any."""
    try:
        os.remove(filename)
        return None
    except OSError as e:
        print("Error: %s - %s." % (e.filename, e.strerror))
        return e.strerror


def delete_folder_recursively(dirpath, delroot=False):
    """Try to delete all files and sub-folders below the given dirpath."""
    if osp.exists(dirpath):
        for filename in os.listdir(dirpath):
            filepath = os.path.join(dirpath, filename)
            try:
                rmtree(filepath)
            except OSError:
                delete_file_safely(filepath)
        if delroot:
            os.rmdir(dirpath)


class SafeFileSaver(QObject):
    """
    A Qt object to manage a save file operation.
    """

    def __init__(self, parent=None, name_filters=None, title=None):
        """
        Parameters
        ----------
        parent : QWidget object, optional
            The parent widget that will be used for the file dialog. If parent
            is not null, the dialog will be shown centered over the
            parent widget.
        name_filters : list of str, optional
            The filters to use in the file dialog.

            See also :func:`set_name_filters`
        title : str, optional
            The window title to use for the getSaveFileName dialog.
            If no title is provided, the getSaveFileName dialog window title
            will be set to _('Save File').
        """
        super().__init__()
        self.parent = parent
        self._savedir = ''
        self.set_name_filters(name_filters)
        self._title = title or _('Save File')

    @property
    def savedir(self):
        """
        Returns the directory last displayed in the getSaveFileName dialog.
        """
        return self._savedir

    def set_name_filters(self, name_filters):
        """
        Sets the filters to use in the file dialog.

        Parameters
        ----------
        name_filters : list of str
            A list of strings corresponding to file filters that will be use
            in the file dialog. Examples of properly formatted filters are
            provided below.

            examples:
                'Image Files (*.png *.jpg *.bmp)'
                'Text files (*.txt)'
                'Any files (*)'
        """
        if name_filters is None or not len(name_filters):
            self._name_filters = 'Any files (*)'
        else:
            self._name_filters = name_filters

    def select_savefilename(self, filename):
        """
        Open a dialog where the user can select a file name.

        Parameters
        ----------
        filename : str
            The absolute path of the selected filename to use initially in the
            dialog. The dialog will also initially display the content of the
            filename's directory if it exists, else the content of the user's
            home directory will be displayed.

            Note that the provided file does not have to exist.

        Returns
        -------
        selected_filename : str or None
            The absolute path of the selected file in the dialog or None if
            no file is selected by the user.
        selected_filter : str or None
            The filter that the user selected in the file dialog or None if
            no file is selected by the user.
        """
        self._savedir = osp.dirname(filename)
        if not osp.exists(osp.dirname(filename)):
            filename = osp.join(get_home_dir(), osp.basename(filename))

        selected_filename, selected_filter = QFileDialog.getSaveFileName(
            self.parent, self._title, filename, ';;'.join(self._name_filters))

        if selected_filename:
            self._savedir = osp.dirname(selected_filename)
            return selected_filename, selected_filter
        else:
            return None, None

    def savefile(self, func, filename, force=False):
        """
        Parameters
        ----------
        func : object
            The method or function that needs to be called to perform the
            save file operation.
        filename : str
            The absolute path of the default selected filename to use for the
            save file operation.
        force : bool
            A flag that can be used to force the save file operation using
            the provided filename without initially showing a save file dialog.
        """
        if force is False:
            filename, selectedfilter = self.select_savefilename(filename)
        if filename:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            QApplication.processEvents()
            try:
                func(filename, selectedfilter)
            except PermissionError:
                self.show_permission_error()
                self.savefile(func, filename, force=False)
            QApplication.restoreOverrideCursor()

    def show_permission_error(self):
        """
        Show a message to warn the user that the saving operation failed.
        """
        QApplication.restoreOverrideCursor()
        msg = _("The save file operation cannot be completed because the "
                "file is in use by another application or user.")
        QMessageBox.warning(self.parent, _('File in Use'), msg, QMessageBox.Ok)
