# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard library imports
import io
import os.path as osp

# ---- Third party imports
from qtpy.QtGui import QImage
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox)

# ---- Local imports
from sardes.config.locale import _
from sardes.config.gui import get_iconsize
from sardes.utils.qthelpers import (
    create_toolbutton, create_mainwindow_toolbar)
from sardes.config.ospath import (
    get_select_file_dialog_dir, set_select_file_dialog_dir)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT


class SardesFigureWidget(QMainWindow):
    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas

        self.setContextMenuPolicy(Qt.NoContextMenu)
        self.setCentralWidget(self.canvas)
        self._setup_toolbar()

    def _setup_toolbar(self):
        """Setup the toolbar of this widget."""
        toolbarname = 'toolbar_{}_{}'.format(
            self.__class__.__name__, id(self))
        self.toolbar = create_mainwindow_toolbar(toolbarname)
        self.addToolBar(self.toolbar)

        self.save_figure_btn = create_toolbutton(
            self, icon='save',
            text=_("Save"),
            tip=_('Save the figure to a file'),
            shortcut='Ctrl+S',
            triggered=lambda: self.canvas.select_and_save_file(),
            iconsize=get_iconsize())
        self.toolbar.addWidget(self.save_figure_btn)

        self.copy_to_clipboard_btn = create_toolbutton(
            self, icon='copy_clipboard',
            text=_("Copy"),
            tip=_("Put a copy of the figure on the Clipboard."),
            triggered=self.canvas.copy_to_clipboard,
            shortcut='Ctrl+C',
            iconsize=get_iconsize())
        self.toolbar.addWidget(self.copy_to_clipboard_btn)


class SardesFigureCanvas(FigureCanvasQTAgg):
    """
    Basic functionality for Sardes figure canvas.
    """
    NAMEFILTERS = {
        '.pdf': 'Portable Document Format (*.pdf)',
        '.svg': 'Scalable Vector Graphics (*.svg)',
        '.png': 'Portable Network Graphics (*.png)',
        '.jpg': 'Joint Photographic Expert Group (*.jpg)'
        }
    SAVEFIGDPI = 600
    CLIPFIGDPI = 300
    MINWIDTH = 450
    MINHEIGHT = 300

    def __init__(self, figure, parent=None):
        """
        Parameters
        ----------
        figure : `matplotlib.figure.Figure`
            A high-level Figure instance.
        """
        super().__init__(figure)
        self.parent = parent
        self.setMinimumSize(self.MINWIDTH, self.MINHEIGHT)

        # Setup a matplotlib navigation toolbar, but hide it.
        toolbar = NavigationToolbar2QT(self, self)
        toolbar.hide()

    def copy_to_clipboard(self):
        """Put a copy of the figure on the clipboard."""
        buf = io.BytesIO()
        self.figure.savefig(buf, dpi=self.CLIPFIGDPI)
        QApplication.clipboard().setImage(QImage.fromData(buf.getvalue()))
        buf.close()

    def get_save_filename(self):
        """
        Return the default aboslute file path to use when saving the image.
        """
        return osp.join(get_select_file_dialog_dir(), _('image.png'))

    def select_and_save_file(self, filename=None):
        """
        Open a file dialog to allow the user to select a file location and type
        and save the figure to the selected file.

        Parameters
        ----------
        filename : str
            The absolute path of the default filename that will be set in
            the file dialog.
        """
        if filename is None:
            filename = self.get_save_filename()

        root, ext = osp.splitext(filename)
        if ext not in self.NAMEFILTERS:
            filename += '.png'
            ext = '.png'
        selected_filter = self.NAMEFILTERS[ext]

        filename, filefilter = QFileDialog.getSaveFileName(
            self.parent,
            _("Save Figure"),
            filename,
            ';;'.join(self.NAMEFILTERS.values()),
            selected_filter
            )
        if filename:
            # Make sur the filename has the right extension.
            ext = dict(map(reversed, self.NAMEFILTERS.items()))[filefilter]
            if not filename.endswith(ext):
                filename += ext

            # Save the target directory to the configs.
            filename = osp.abspath(filename)
            set_select_file_dialog_dir(osp.dirname(filename))

            # Save the figure to file.
            self.save_file(filename)

    def save_file(self, filename):
        """
        Plot and save the resampled and formatted readings data of this tool's
        parent table to pdf, svg, png or jpg file.
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()
        try:
            self.figure.savefig(filename, dpi=self.SAVEFIGDPI)
        except PermissionError:
            QApplication.restoreOverrideCursor()
            QApplication.processEvents()
            QMessageBox.warning(
                self.parent,
                _('File in Use'),
                _("The save file operation cannot be completed because the "
                  "file is in use by another application or user."),
                QMessageBox.Ok)
            self.select_and_save_file(filename)
        else:
            QApplication.restoreOverrideCursor()
            QApplication.processEvents()


if __name__ == '__main__':
    import sys
    import matplotlib.pyplot as plt
    app = QApplication(sys.argv)

    figure, ax = plt.subplots(1, 1)
    ax.plot([1, 2, 3], [1, 2, 3], '.')

    canvas = SardesFigureCanvas(figure)
    widget = SardesFigureWidget(canvas)

    widget.show()

    sys.exit(app.exec_())
