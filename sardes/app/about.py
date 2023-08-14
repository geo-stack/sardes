# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/geo-stack/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""About Sardes dialog."""

# ---- Standard imports
import sys
import os.path as osp

# ---- Third party imports
from qtpy.QtCore import Qt
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QFrame)

# ---- Local imports
from sardes import get_versions, __rootdir__
from sardes.config.icons import get_icon
from sardes.config.locale import _


class AboutDialog(QDialog):

    def __init__(self, parent=None):
        """Create About Sardes dialog with general information."""
        super().__init__(parent=parent)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setWindowIcon(get_icon('information'))
        self.setWindowTitle(_("About Sardes"))
        versions = get_versions()

        # Get current font properties
        font = self.font()
        font_family = font.family()
        font_size = font.pointSize()
        contributors = _("Sardes Project Contributors")
        longdesc = "<p>" + _(
            "Sardes is an open-source software designed for storing, "
            "managing, visualizing, and interpreting data from a groundwater "
            "monitoring network. "
            "See the project's GitHub repository for more information."
            ""
            ) + "</p>"
        self.label = QLabel(_(
            """
            <div style='font-family: "{font_family}";
                        font-size: {font_size}pt;
                        font-weight: normal;
                        '>
            <p>
            <br><b>Sardes {sardes_ver}</b><br>
            Copyright &copy; {contributors}<br>
            <a href="{website_url}">https://github.com/geo-stack/sardes</a>
            </p>
            <p>{longdesc}</p>
            <p>
            Python {python_ver} {bitness}-bit | Qt {qt_ver} |
            {qt_api} {qt_api_ver} | {os_name} {os_ver}
            </p>
            </div>
            """.format(
                sardes_ver=versions['sardes'],
                website_url='https://github.com/geo-stack/sardes',
                python_ver=versions['python'],
                bitness=versions['bitness'],
                qt_ver=versions['qt'],
                qt_api=versions['qt_api'],
                qt_api_ver=versions['qt_api_ver'],
                os_name=versions['system'],
                os_ver=versions['release'],
                font_family=font_family,
                font_size=font_size,
                contributors=contributors,
                longdesc=longdesc
            )
        ))
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignTop)
        self.label.setOpenExternalLinks(True)
        self.label.setTextInteractionFlags(Qt.TextBrowserInteraction)

        pixmap = QPixmap(osp.join(
            __rootdir__, 'ressources', 'sardes_banner.png'))
        self.label_pic = QLabel(self)
        self.label_pic.setPixmap(
            pixmap.scaledToWidth(450, Qt.SmoothTransformation))
        self.label_pic.setAlignment(Qt.AlignTop)

        content_frame = QFrame(self)
        content_frame.setStyleSheet(
            "QFrame {background-color: white}")
        content_layout = QVBoxLayout(content_frame)
        content_layout.addWidget(self.label_pic)
        content_layout.addWidget(self.label)
        content_layout.setContentsMargins(15, 15, 15, 15)

        bbox = QDialogButtonBox(QDialogButtonBox.Ok)
        bbox.accepted.connect(self.accept)

        # Setup the layout.
        layout = QVBoxLayout(self)
        layout.addWidget(content_frame)
        layout.addWidget(bbox)
        layout.setSizeConstraint(layout.SetFixedSize)

    def show(self):
        """Overide Qt method."""
        super().show()
        self.activateWindow()
        self.raise_()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    about = AboutDialog()
    about.show()
    sys.exit(app.exec_())
