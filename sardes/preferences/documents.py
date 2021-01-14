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
    QApplication, QGroupBox, QGridLayout, QLabel, QLineEdit, QFontComboBox)

# ---- Local imports
from sardes.config.locale import _
from sardes.config.ospath import CONFIG_DIR, CONF, get_documents_logo_filename
from sardes.preferences.configdialog import ConfPage
from sardes.widgets.logoselector import LogoSelector

CONF_SECTION = 'documents_settings'


class DocumentsSettingsConfPage(ConfPage):

    # ---- ConfPage API
    def __init__(self):
        super().__init__(
            name='documents_settings_confpage',
            label=_('Documents Settings'),
            iconname='file_settings'
            )

    def setup_page(self):
        # Setup the logo groupbox.
        self.logo_selector = LogoSelector()
        self.logo_selector.sig_logo_changed.connect(
            lambda: self.sig_settings_changed.emit())

        logo_groupbox = QGroupBox(_("Logo"))
        logo_layout = QGridLayout(logo_groupbox)
        logo_layout.addWidget(self.logo_selector, 0, 0)
        logo_layout.setRowStretch(1, 1)

        # Setup the information groupbox.
        self.site_url_lineedit = QLineEdit()
        self.site_url_lineedit.textChanged.connect(
            lambda: self.sig_settings_changed.emit())

        self.authors_name_lineedit = QLineEdit()
        self.authors_name_lineedit.textChanged.connect(
            lambda: self.sig_settings_changed.emit())

        ref_groupbox = QGroupBox(_('References'))
        ref_layout = QGridLayout(ref_groupbox)
        ref_layout.addWidget(QLabel(_("Site URL:")), 0, 0)
        ref_layout.addWidget(self.site_url_lineedit, 0, 1)
        ref_layout.addWidget(QLabel(_("Author's Name:")), 1, 0)
        ref_layout.addWidget(self.authors_name_lineedit, 1, 1)
        ref_layout.setColumnMinimumWidth(1, 350)

        # Setup the font groupbox.
        self.xlsx_font_combobox = QFontComboBox()
        self.xlsx_font_combobox.currentFontChanged.connect(
            lambda: self.sig_settings_changed.emit())
        self.graph_font_combobox = QFontComboBox()
        self.graph_font_combobox.currentFontChanged.connect(
            lambda: self.sig_settings_changed.emit())

        fonts_groupbox = QGroupBox(_('Fonts'))
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

    def get_settings(self):
        """Return the settings that are set in this configuration page."""
        return {
            'logo_filename': self.logo_selector.filename,
            'site_url': self.site_url_lineedit.text(),
            'authors_name': self.authors_name_lineedit.text(),
            'xlsx_font': self.xlsx_font_combobox.currentFont().family(),
            'graph_font': self.graph_font_combobox.currentFont().family(),
            }

    def get_settings_from_conf(self):
        return {
            'logo_filename': get_documents_logo_filename(),
            'site_url': CONF.get(CONF_SECTION, 'site_url', ''),
            'authors_name': CONF.get(CONF_SECTION, 'authors_name', ''),
            'xlsx_font': CONF.get(CONF_SECTION, 'xlsx_font'),
            'graph_font': CONF.get(CONF_SECTION, 'graph_font'),
            }

    def load_settings_from_conf(self):
        settings = self.get_settings_from_conf()
        self.logo_selector.load_image(settings['logo_filename'])
        self.site_url_lineedit.setText(settings['site_url'])
        self.authors_name_lineedit.setText(settings['authors_name'])
        self.xlsx_font_combobox.setCurrentFont(QFont(settings['xlsx_font']))
        self.graph_font_combobox.setCurrentFont(QFont(settings['graph_font']))

    def save_settings_to_conf(self):
        settings = self.get_settings()

        # Save fonts.
        CONF.set(CONF_SECTION, 'xlsx_font', settings['xlsx_font'])
        CONF.set(CONF_SECTION, 'graph_font', settings['graph_font'])

        # Save references.
        CONF.set(CONF_SECTION, 'site_url', settings['site_url'])
        CONF.set(CONF_SECTION, 'authors_name', settings['authors_name'])

        # Save logo.
        new_logo_filename = settings['logo_filename']
        conf_logo_filename = get_documents_logo_filename()
        if new_logo_filename != conf_logo_filename:
            # Clean up the old logo file from the config folder if any.
            if conf_logo_filename and osp.exists(conf_logo_filename):
                os.remove(conf_logo_filename)

            # Copy the new logo file to the config folder if not None.
            if new_logo_filename and osp.exists(new_logo_filename):
                conf_logo_filename = osp.join(
                    CONFIG_DIR, osp.basename(new_logo_filename))
                shutil.copyfile(new_logo_filename, conf_logo_filename)
                CONF.set(CONF_SECTION, 'logo_filename', conf_logo_filename)

                # We need to change the logo selector filepath to that of the
                # file we just copied in the config folder to ensure
                # 'is_modified' returns False.
                self.logo_selector._filename = conf_logo_filename


if __name__ == '__main__':
    app = QApplication(sys.argv)
    img_selector = LogoSelector()
    img_selector.show()
    sys.exit(app.exec_())
