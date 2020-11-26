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
import os.path as osp
import sys
import shutil

# ---- Third party imports
from qtpy.QtGui import QFont
from qtpy.QtWidgets import (
    QApplication, QWidget, QGroupBox, QGridLayout, QLabel, QLineEdit,
    QFontComboBox)

# ---- Local imports
from sardes.config.locale import _
from sardes.config.icons import get_icon
from sardes.config.ospath import CONFIG_DIR, CONF, get_documents_logo_filename
from sardes.preferences.configdialog import ConfPage
from sardes.widgets.logoselector import LogoSelector

CONF_SECTION = 'documents_settings'


class DocumentsSettingsConfPage(ConfPage):

    # ---- ConfPage API
    def setup_page(self):
        # Setup the logo groupbox.
        self.logo_selector = LogoSelector()

        logo_groupbox = QGroupBox(_("Logo"))
        logo_layout = QGridLayout(logo_groupbox)
        logo_layout.addWidget(self.logo_selector, 0, 0)
        logo_layout.setRowStretch(1, 1)

        # Setup the information groupbox.
        self.site_url_lineedit = QLineEdit()
        self.authors_name_lineedit = QLineEdit()

        ref_groupbox = QGroupBox('References')
        ref_layout = QGridLayout(ref_groupbox)
        ref_layout.addWidget(QLabel(_("Site URL:")), 0, 0)
        ref_layout.addWidget(self.site_url_lineedit, 0, 1)
        ref_layout.addWidget(QLabel(_("Author's Name:")), 1, 0)
        ref_layout.addWidget(self.authors_name_lineedit, 1, 1)
        ref_layout.setColumnMinimumWidth(1, 350)

        # Setup the font groupbox.
        self.xlsx_font_combobox = QFontComboBox()
        self.graph_font_combobox = QFontComboBox()

        fonts_groupbox = QGroupBox('Fonts')
        fonts_layout = QGridLayout(fonts_groupbox)
        fonts_layout.addWidget(QLabel(_("XLSX Documents:")), 0, 0)
        fonts_layout.addWidget(self.xlsx_font_combobox, 0, 1)
        fonts_layout.addWidget(QLabel(_("Graphs:")), 1, 0)
        fonts_layout.addWidget(self.graph_font_combobox, 1, 1)
        fonts_layout.setColumnStretch(2, 1)

        # Setup the main layout.
        main_layout = QGridLayout(self)
        main_layout.addWidget(logo_groupbox, 0, 0)
        main_layout.addWidget(ref_groupbox, 1, 0)
        main_layout.addWidget(fonts_groupbox, 2, 0)
        main_layout.setRowStretch(3, 1)

        self.load_from_conf()

    def get_name(self):
        return 'documents_settings_confpage'

    def get_label(self):
        return _('Documents Settings')

    def get_icon(self):
        return get_icon('file_excel')

    def get_from_conf(self):
        """Get settings from configuration file."""
        return {
            'logo_filename': get_documents_logo_filename(),
            'site_url': CONF.get(CONF_SECTION, 'site_url', ''),
            'authors_name': CONF.get(CONF_SECTION, 'authors_name', ''),
            'xlsx_font': CONF.get(CONF_SECTION, 'xlsx_font'),
            'graph_font': CONF.get(CONF_SECTION, 'graph_font'),
            }

    def apply_changes(self):
        """Apply changes."""
        self.save_to_conf()

    def load_from_conf(self):
        """Load settings from configuration file."""
        options = self.get_from_conf()
        self.logo_selector.load_image(options['logo_filename'])
        self.site_url_lineedit.setText(options['site_url'])
        self.authors_name_lineedit.setText(options['authors_name'])
        self.xlsx_font_combobox.setCurrentFont(QFont(options['xlsx_font']))
        self.graph_font_combobox.setCurrentFont(QFont(options['graph_font']))

    def save_to_conf(self):
        """Save settings to configuration file."""
        # Save fonts.
        CONF.set(CONF_SECTION, 'xlsx_font',
                 self.xlsx_font_combobox.currentFont().family())
        CONF.set(CONF_SECTION, 'graph_font',
                 self.graph_font_combobox.currentFont().family())

        # Save references.
        CONF.set(CONF_SECTION, 'site_url', self.site_url_lineedit.text())
        CONF.set(CONF_SECTION, 'authors_name',
                 self.authors_name_lineedit.text())

        # Save logo.
        new_logo_filename = self.logo_selector.filename
        conf_logo_filename = get_documents_logo_filename()
        if new_logo_filename != conf_logo_filename:
            # Clean up the old logo file from the config folder if any.
            if conf_logo_filename and osp.exists(conf_logo_filename):
                os.remove(conf_logo_filename)

            # Copy the new logo file to the config folder if not None.
            new_logo_filename = self.logo_selector.filename
            if new_logo_filename and osp.exists(new_logo_filename):
                conf_logo_filename = osp.join(
                    CONFIG_DIR, osp.basename(new_logo_filename))
                shutil.copyfile(new_logo_filename, conf_logo_filename)
                CONF.set(CONF_SECTION, 'logo_filename', conf_logo_filename)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    img_selector = LogoSelector()
    img_selector.show()
    sys.exit(app.exec_())
