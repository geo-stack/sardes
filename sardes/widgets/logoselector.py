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
import sys

# ---- Third party imports
import qtawesome as qta
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QColor, QPixmap
from qtpy.QtWidgets import (
    QApplication, QPushButton, QWidget, QGraphicsDropShadowEffect,
    QGridLayout, QLabel, QFileDialog)

# ---- Local imports
from sardes.config.locale import _
from sardes.config.ospath import (
    get_select_file_dialog_dir, set_select_file_dialog_dir)


class LogoSelector(QWidget):
    """
    A widget to select and display a logo.
    """
    sig_logo_changed = Signal()
    FILEFILTER = 'Image (*.png ; *.bmp ; *.jpg ; *.jpeg ; *.tif)'

    def __init__(self, filename=None, parent=None, logo_size=250):
        super().__init__(parent=parent)
        self.logo_size = 250
        self._filename = filename

        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(5)
        effect.setXOffset(3)
        effect.setYOffset(3)
        effect.setColor(QColor('#999999'))

        self.logo_preview_label = QLabel()
        self.logo_preview_label.setStyleSheet(
            "QLabel {background-color : white; border: 1px solid #b3b3b3}")
        self.logo_preview_label.setGraphicsEffect(effect)
        self.logo_preview_label.setScaledContents(False)

        # We want to load the default image even if filename is not None in
        # case there is an error while loading the image.
        self.load_default_image()
        if filename is not None:
            self.load_image(filename)

        logo_group = QWidget()
        logo_group.setFixedWidth(self.logo_size + 12)
        logo_layout = QGridLayout(logo_group)
        logo_layout.setContentsMargins(0, 0, 0, 8)
        logo_layout.addWidget(self.logo_preview_label, 1, 1)
        logo_layout.setColumnStretch(0, 1)
        logo_layout.setColumnStretch(2, 1)

        self.browse_logo_button = QPushButton(_('Change Logo...'))
        self.browse_logo_button.clicked.connect(self.browse_image)
        self.remove_logo_button = QPushButton(_('Remove Logo'))
        self.remove_logo_button.clicked.connect(self.load_default_image)

        layout = QGridLayout(self)
        layout.addWidget(logo_group, 0, 1, 1, 2)
        layout.addWidget(self.browse_logo_button, 1, 1)
        layout.addWidget(self.remove_logo_button, 1, 2)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(3, 1)
        layout.setRowStretch(layout.rowCount(), 1)

    @property
    def filename(self):
        """
        Return the absolute filepath of the image that is currently
        displayed as the logo.
        """
        return (None if self._filename is None else
                osp.abspath(self._filename))

    def browse_image(self):
        """
        Open a dialog that allows the used to select an image to display
        as the logo.
        """
        filename, filefilter = QFileDialog.getOpenFileName(
            self.parent() or self,
            _('Select Image'),
            get_select_file_dialog_dir(),
            self.FILEFILTER
            )
        if filename:
            set_select_file_dialog_dir(osp.dirname(filename))
            self.load_image(filename)

    def load_image(self, filename):
        """
        Read and display the image at the specified filename as the logo.
        """
        if filename is None or not osp.exists(filename):
            self.load_default_image()
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()
        try:
            qpixmap = QPixmap(filename)
            size = qpixmap.size()
            if size.width() >= size.height():
                qpixmap = qpixmap.scaledToWidth(
                    self.logo_size, Qt.SmoothTransformation)
            else:
                qpixmap = qpixmap.scaledToHeight(
                    self.logo_size, Qt.SmoothTransformation)
        except Exception as e:
            print(e)
        else:
            self.logo_preview_label.setPixmap(qpixmap)
            self._filename = filename
        QApplication.restoreOverrideCursor()
        QApplication.processEvents()
        self.sig_logo_changed.emit()

    def load_default_image(self):
        """
        Display a generic image to indicate to the user that no logo is
        currently selected.
        """
        self._filename = None
        default_image = qta.icon(
            'fa.image', color='#b3b3b3'
            ).pixmap(self.logo_size, self.logo_size)
        self.logo_preview_label.setPixmap(default_image)
        self.sig_logo_changed.emit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    img_selector = LogoSelector()
    img_selector.show()
    sys.exit(app.exec_())
